from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Final

import aiosqlite
import ollama
from langchain.agents import create_agent
from langchain.messages import AIMessageChunk, HumanMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_demo import probe
from rag_demo.constants import LocalProviderType

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from rag_demo.app_protocol import AppProtocol


class OllamaAgent:
    """An LLM agent powered by Ollama."""

    def __init__(self, checkpoints_conn: aiosqlite.Connection) -> None:
        """Initialize the OllamaAgent.

        Args:
            checkpoints_conn (aiosqlite.Connection): Asynchronous connection to SQLite db for checkpoints.
        """
        self.checkpoints_conn = checkpoints_conn
        ollama.pull("gemma3:latest")  # 3.3GB
        ollama.pull("embeddinggemma:latest")  # 621MB
        self.llm = ChatOllama(
            model="gemma3:latest",
            validate_model_on_init=True,
            temperature=0.5,
            num_predict=4096,
        )
        self.embed = OllamaEmbeddings(model="embeddinggemma:latest")
        self.agent = create_agent(
            model=self.llm,
            system_prompt="You are a helpful assistant.",
            checkpointer=AsyncSqliteSaver(self.checkpoints_conn),
        )

    async def astream(self, user_message: str, thread_id: str, app: AppProtocol) -> AsyncIterator[str]:
        """Stream a response from the agent.

        Args:
            user_message (str): User's next prompt in the conversation.
            thread_id (str): Identifier for the current thread/conversation.
            app (AppProtocol): Application interface, commonly used for logging.

        Yields:
            str: A token from the agent's response.
        """
        agent_stream = self.agent.astream(
            {"messages": [HumanMessage(content=user_message)]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="messages",
        )
        async for message_chunk, _ in agent_stream:
            if isinstance(message_chunk, AIMessageChunk):
                token = message_chunk.content
                if isinstance(token, str):
                    yield token
                else:
                    app.log.error("Received message content of type", type(token))
            else:
                app.log.error("Received message chunk of type", type(message_chunk))


class OllamaAgentProvider:
    """Create LLM agents using Ollama."""

    type: Final[LocalProviderType] = LocalProviderType.OLLAMA

    @asynccontextmanager
    async def get_agent(self, checkpoints_sqlite_db: str | Path) -> AsyncIterator[OllamaAgent | None]:
        """Attempt to create an Ollama agent.

        Args:
            checkpoints_sqlite_db (str | Path): Connection string for SQLite database used for LangChain checkpoints.
        """
        if probe.probe_ollama() is not None:
            async with aiosqlite.connect(database=checkpoints_sqlite_db) as checkpoints_conn:
                yield OllamaAgent(checkpoints_conn=checkpoints_conn)
        else:
            yield None
