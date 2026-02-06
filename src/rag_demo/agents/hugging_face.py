from __future__ import annotations

import asyncio
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

    def __init__(
        self,
        checkpoints_sqlite_db: str | Path,
        model_id: str,
        embedding_model_id: str,
    ) -> None:
        """Initialize the HuggingFaceAgent.

        Args:
            checkpoints_sqlite_db (str | Path): Connection string for SQLite database used for LangChain checkpoints.
            model_id (str): Hugging Face model ID for the LLM.
            embedding_model_id (str): Hugging Face model ID for the embedding model.
        """
        self.checkpoints_sqlite_db = checkpoints_sqlite_db
        self.model_id = model_id
        self.embedding_model_id = embedding_model_id

        self.llm = ChatHuggingFace(
            llm=HuggingFacePipeline.from_model_id(
                model_id=model_id,
                task="text-generation",
                device_map="auto",
                pipeline_kwargs={"max_new_tokens": 4096},
            ),
        )
        self.embed = HuggingFaceEmbeddings(model_name=embedding_model_id)
        self.agent = create_agent(
            model=self.llm,
            system_prompt="You are a helpful assistant.",
            checkpointer=SqliteSaver(sqlite3.Connection(self.checkpoints_sqlite_db, check_same_thread=False)),
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


def _hf_downloads() -> None:
    hf_hub_download(
        repo_id="Qwen/Qwen3-0.6B",  # 1.5GB
        filename="model.safetensors",
        revision="c1899de289a04d12100db370d81485cdf75e47ca",
    )
    hf_hub_download(
        repo_id="unsloth/embeddinggemma-300m",  # 1.21GB
        filename="model.safetensors",
        revision="bfa3c846ac738e62aa61806ef9112d34acb1dc5a",
    )


class HuggingFaceAgentProvider:
    """Create LLM agents using Hugging Face local pipelines."""

    type: Final[LocalProviderType] = LocalProviderType.HUGGING_FACE

    @asynccontextmanager
    async def get_agent(self, checkpoints_sqlite_db: str | Path) -> AsyncIterator[HuggingFaceAgent]:
        """Create a Hugging Face local pipeline agent.

        Args:
            checkpoints_sqlite_db (str | Path): Connection string for SQLite database used for LangChain checkpoints.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _hf_downloads)
        yield HuggingFaceAgent(
            checkpoints_sqlite_db,
            model_id="Qwen/Qwen3-0.6B",
            embedding_model_id="unsloth/embeddinggemma-300m",
        )
