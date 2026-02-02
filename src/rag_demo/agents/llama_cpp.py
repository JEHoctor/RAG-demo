from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Final

import aiosqlite
from huggingface_hub import hf_hub_download
from langchain.agents import create_agent
from langchain.messages import AIMessageChunk, HumanMessage
from langchain_community.chat_models import ChatLlamaCpp
from langchain_community.embeddings import LlamaCppEmbeddings
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_demo import probe
from rag_demo.constants import LocalProviderType

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from rag_demo.app_protocol import AppProtocol


class LlamaCppAgent:
    """An LLM agent powered by Llama.cpp."""

    def __init__(self, checkpoints_conn: aiosqlite.Connection) -> None:
        """Initialize the LlamaCppAgent.

        Args:
            checkpoints_conn (aiosqlite.Connection): Asynchronous connection to SQLite db for checkpoints.
        """
        self.checkpoints_conn = checkpoints_conn
        model_path = hf_hub_download(
            repo_id="bartowski/google_gemma-3-4b-it-GGUF",
            filename="google_gemma-3-4b-it-Q6_K_L.gguf",  # 3.35GB
            revision="71506238f970075ca85125cd749c28b1b0eee84e",
        )
        embedding_model_path = hf_hub_download(
            repo_id="CompendiumLabs/bge-small-en-v1.5-gguf",
            filename="bge-small-en-v1.5-q8_0.gguf",  # 36.8MB
            revision="d32f8c040ea3b516330eeb75b72bcc2d3a780ab7",
        )
        self.llm = ChatLlamaCpp(model_path=model_path, verbose=False)
        self.embed = LlamaCppEmbeddings(model_path=embedding_model_path, verbose=False)
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


class LlamaCppAgentProvider:
    """Create LLM agents using Llama.cpp."""

    type: Final[LocalProviderType] = LocalProviderType.LLAMA_CPP

    @asynccontextmanager
    async def get_agent(self, checkpoints_sqlite_db: str | Path) -> AsyncIterator[LlamaCppAgent | None]:
        """Attempt to create a Llama.cpp agent.

        Args:
            checkpoints_sqlite_db (str | Path): Connection string for SQLite database used for LangChain checkpoints.
        """
        if probe.probe_llama_available():
            async with aiosqlite.connect(database=checkpoints_sqlite_db) as checkpoints_conn:
                yield LlamaCppAgent(
                    checkpoints_conn=checkpoints_conn,
                )
        else:
            yield None
