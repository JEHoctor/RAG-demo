from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Final

from huggingface_hub import hf_hub_download
from langchain.agents import create_agent
from langchain.messages import AIMessageChunk, HumanMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEmbeddings, HuggingFacePipeline
from langgraph.checkpoint.sqlite import SqliteSaver

from rag_demo.constants import LocalProviderType

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from rag_demo.app_protocol import AppProtocol


class HuggingFaceAgent:
    """An LLM agent powered by Hugging Face local pipelines."""

    def __init__(self, checkpoints_sqlite_db: str | Path) -> None:
        """Initialize the HuggingFaceAgent.

        Args:
            checkpoints_sqlite_db (str | Path): Connection string for SQLite database used for LangChain checkpoints.
        """
        self.checkpoints_sqlite_db = checkpoints_sqlite_db
        hf_hub_download(
            repo_id="unsloth/gemma-3-4b-it-bnb-4bit",  # 3.23GB
            filename="model.safetensors",
            revision="eb03c885bc2cc913fe792994bc766006f14ad72d",
        )
        self.llm = ChatHuggingFace(
            llm=HuggingFacePipeline.from_model_id(
                model_id="unsloth/gemma-3-4b-it-bnb-4bit",  # 3.23GB
                task="text-generation",
                device_map="auto",
                pipeline_kwargs={"max_new_tokens": 4096},
            ),
        )
        self.embed = HuggingFaceEmbeddings(model_name="unsloth/embeddinggemma-300m")  # 1.21GB
        self.agent = create_agent(
            model=self.llm,
            system_prompt="You are a helpful assistant.",
            checkpointer=SqliteSaver(sqlite3.Connection(self.checkpoints_sqlite_db)),
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
        agent_stream = self.agent.stream(
            {"messages": [HumanMessage(content=user_message)]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="messages",
        )
        for message_chunk, _ in agent_stream:
            if isinstance(message_chunk, AIMessageChunk):
                token = message_chunk.content
                if isinstance(token, str):
                    yield token
                else:
                    app.log.error("Received message content of type", type(token))
            else:
                app.log.error("Received message chunk of type", type(message_chunk))


class HuggingFaceAgentProvider:
    """Create LLM agents using Hugging Face local pipelines."""

    type: Final[LocalProviderType] = LocalProviderType.HUGGING_FACE

    @asynccontextmanager
    async def get_agent(self, checkpoints_sqlite_db: str | Path) -> AsyncIterator[HuggingFaceAgent]:
        """Create a Hugging Face local pipeline agent.

        Args:
            checkpoints_sqlite_db (str | Path): Connection string for SQLite database used for LangChain checkpoints.
        """
        yield HuggingFaceAgent(checkpoints_sqlite_db)
