from __future__ import annotations

from typing import TYPE_CHECKING, Final, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from contextlib import AbstractAsyncContextManager

    from rag_demo.app_protocol import AppProtocol
    from rag_demo.constants import LocalProviderType


class Agent(Protocol):
    """An LLM agent that supports streaming responses asynchronously."""

    def astream(self, user_message: str, thread_id: str, app: AppProtocol) -> AsyncIterator[str]:
        """Stream a response from the agent.

        Args:
            user_message (str): User's next prompt in the conversation.
            thread_id (str): Identifier for the current thread/conversation.
            app (AppProtocol): Application interface, commonly used for logging.

        Yields:
            str: A token from the agent's response.
        """


class AgentProvider(Protocol):
    """A strategy for creating LLM agents."""

    type: Final[LocalProviderType]

    def get_agent(self) -> AbstractAsyncContextManager[Agent | None]:
        """Attempt to create an agent."""
