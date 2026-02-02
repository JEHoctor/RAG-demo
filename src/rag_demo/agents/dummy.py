from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Final

from rag_demo.constants import LocalProviderType

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence
    from pathlib import Path

    from rag_demo.app_protocol import AppProtocol


class DummyAgent:
    """An LLM agent that always replies with the same message."""

    def __init__(self, response: Sequence[str] = ("Hello", ",", " World", "!"), delay: float = 0.02) -> None:
        """Initialize the DummyAgent.

        Args:
            response (Sequence[str], optional): The response as a sequence of token strings.
                Defaults to ("Hello", ",", " World", "!").
            delay (float, optional): The delay between tokens in seconds. Defaults to 0.02.
        """
        self.response = response
        self.delay = delay

    async def astream(self, user_message: str, thread_id: str, app: AppProtocol) -> AsyncIterator[str]:
        """Stream a response from the agent.

        Args:
            user_message (str): User's next prompt in the conversation.
            thread_id (str): Identifier for the current thread/conversation.
            app (AppProtocol): Application interface, commonly used for logging.

        Yields:
            str: A token from the agent's response.
        """
        del user_message, thread_id, app
        for token in self.response:
            yield token
            await asyncio.sleep(delay=self.delay)


class DummyAgentProvider:
    """Create dummy LLM agents."""

    type: Final[LocalProviderType] = LocalProviderType.DUMMY

    @asynccontextmanager
    async def get_agent(self, checkpoints_sqlite_db: str | Path) -> AsyncIterator[DummyAgent | None]:
        """Create a dummy agent.

        Args:
            checkpoints_sqlite_db (str | Path): Connection string for SQLite database used for LangChain checkpoints.
        """
        del checkpoints_sqlite_db
        yield DummyAgent()
