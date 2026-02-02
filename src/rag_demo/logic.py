from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

from datasets import Dataset, load_dataset
from langchain_core.exceptions import LangChainException

from rag_demo import dirs
from rag_demo.agents import (
    Agent,
    AgentProvider,
    HuggingFaceAgentProvider,
    LlamaCppAgentProvider,
    OllamaAgentProvider,
)
from rag_demo.db import AtomicIDManager
from rag_demo.modes.chat import Response, StoppedStreamError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence
    from pathlib import Path

    from rag_demo.app_protocol import AppProtocol
    from rag_demo.constants import LocalProviderType
    from rag_demo.modes import ChatScreen


class UnknownPreferredProviderError(ValueError):
    """Raised when the preferred provider cannot be checked first due to being unknown."""

    def __init__(self, preferred_provider: LocalProviderType) -> None:  # noqa: D107
        super().__init__(f"Unknown preferred provider: {preferred_provider}")


class NoProviderError(RuntimeError):
    """Raised when no provider could provide an agent."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__("No provider could provide an agent.")


class Runtime:
    """The application logic with asynchronously initialized resources."""

    def __init__(
        self,
        logic: Logic,
        app: AppProtocol,
        agent: Agent,
        thread_id_manager: AtomicIDManager,
    ) -> None:
        """Initialize the runtime.

        Args:
            logic (Logic): The application logic.
            app (AppProtocol): The application interface.
            agent (Agent): The agent to use.
            thread_id_manager (AtomicIDManager): The thread ID manager.
        """
        self.runtime_start_time = time.time()
        self.logic = logic
        self.app = app
        self.agent = agent
        self.thread_id_manager = thread_id_manager

        self.current_thread: int | None = None
        self.generating = False

    def _get_rag_datasets(self) -> None:
        self.qa_test: Dataset = cast(
            "Dataset",
            load_dataset("rag-datasets/rag-mini-wikipedia", "question-answer", split="test"),
        )
        self.corpus: Dataset = cast(
            "Dataset",
            load_dataset("rag-datasets/rag-mini-wikipedia", "text-corpus", split="passages"),
        )

    async def stream_response(self, response_widget: Response, request_text: str, thread: str) -> None:
        """Worker method for streaming tokens from the active agent to a response widget.

        Args:
            response_widget (Response): Target response widget for streamed tokens.
            request_text (str): Text of the user request.
            thread (str): ID of the current thread.
        """
        self.generating = True
        async with response_widget.stream_writer() as writer:
            try:
                async for message_chunk in self.agent.astream(request_text, thread, self.app):
                    await writer.write(message_chunk)
            except StoppedStreamError as e:
                response_widget.set_shown_object(e)
            except LangChainException as e:
                response_widget.set_shown_object(e)
        self.generating = False

    def new_conversation(self, chat_screen: ChatScreen) -> None:
        """Clear the screen and start a new conversation with the agent.

        Args:
            chat_screen (ChatScreen): The chat screen to clear.
        """
        self.current_thread = None
        chat_screen.clear_chats()

    async def submit_request(self, chat_screen: ChatScreen, request_text: str) -> bool:
        """Submit a new user request in the current conversation.

        Args:
            chat_screen (ChatScreen): The chat screen in which the request is submitted.
            request_text (str): The text of the request.

        Returns:
            bool: True if the request was accepted for immediate processing, False otherwise.
        """
        if self.generating:
            return False
        self.generating = True
        if self.current_thread is None:
            chat_screen.log.info("Starting new thread")
            self.current_thread = await self.thread_id_manager.claim_next_id()
            chat_screen.log.info("Claimed thread id", self.current_thread)
        chat_screen.new_request(request_text)
        response = chat_screen.new_response()
        chat_screen.run_worker(self.stream_response(response, request_text, str(self.current_thread)))
        return True


class Logic:
    """Top-level application logic."""

    def __init__(
        self,
        username: str | None = None,
        preferred_provider_type: LocalProviderType | None = None,
        application_start_time: float | None = None,
        checkpoints_sqlite_db: str | Path = dirs.DATA_DIR / "checkpoints.sqlite3",
        app_sqlite_db: str | Path = dirs.DATA_DIR / "app.sqlite3",
        agent_providers: Sequence[AgentProvider] = (
            LlamaCppAgentProvider(),
            OllamaAgentProvider(),
            HuggingFaceAgentProvider(),
        ),
    ) -> None:
        """Initialize the application logic.

        Args:
            username (str | None, optional): The username provided as a command line argument. Defaults to None.
            preferred_provider_type (LocalProviderType | None, optional): Provider type to prefer. Defaults to None.
            application_start_time (float | None, optional): The time when the application started. Defaults to None.
            checkpoints_sqlite_db (str | Path, optional): The connection string for the SQLite database used for
                Langchain checkpointing. Defaults to (dirs.DATA_DIR / "checkpoints.sqlite3").
            app_sqlite_db (str | Path, optional): The connection string for the SQLite database used for application
                state such a thread metadata. Defaults to (dirs.DATA_DIR / "app.sqlite3").
            agent_providers (Sequence[AgentProvider], optional): Sequence of agent providers in default preference
                order. If preferred_provider_type is not None, this sequence will be reordered to bring providers of
                that type to the front, using the original order to break ties. Defaults to (
                    LlamaCppAgentProvider(),
                    OllamaAgentProvider(),
                    HuggingFaceAgentProvider(),
                ).
        """
        self.logic_start_time = time.time()
        self.username = username
        self.preferred_provider_type = preferred_provider_type
        self.application_start_time = application_start_time
        self.checkpoints_sqlite_db = checkpoints_sqlite_db
        self.app_sqlite_db = app_sqlite_db
        self.agent_providers: Sequence[AgentProvider] = agent_providers

    @asynccontextmanager
    async def runtime(self, app: AppProtocol) -> AsyncIterator[Runtime]:
        """Returns a runtime context for the application."""
        thread_id_manager = AtomicIDManager(self.app_sqlite_db)
        await thread_id_manager.initialize()

        agent_providers: Sequence[AgentProvider] = self.agent_providers
        if self.preferred_provider_type is not None:
            preferred_providers: Sequence[AgentProvider] = tuple(
                ap for ap in agent_providers if ap.type == self.preferred_provider_type
            )
            if len(preferred_providers) == 0:
                raise UnknownPreferredProviderError(self.preferred_provider_type)
            agent_providers = tuple(
                *preferred_providers,
                *(ap for ap in agent_providers if ap.type != self.preferred_provider_type),
            )
        for agent_provider in agent_providers:
            async with agent_provider.get_agent(checkpoints_sqlite_db=self.checkpoints_sqlite_db) as agent:
                if agent is not None:
                    yield Runtime(
                        logic=self,
                        app=app,
                        agent=agent,
                        thread_id_manager=thread_id_manager,
                    )
                    return
        raise NoProviderError
