"""Interface for the logic to call back into the app code.

This is necessary to make the logic code testable. We don't want to have to run all the app code to test the logic. And,
we want to have a high degree of confidence when mocking out the app code in logic tests. The basic pattern is that each
piece of functionality that the logic depends on will have a protocol and an implementation of that protocol using the
Textual App. In the tests, we create a mock implementation of the same protocol. Correctness of the logic is defined by
its ability to work correctly with any implementation of the protocol, not just the implementation backed by the app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from textual.worker import Worker


class LoggerProtocol(Protocol):
    """Protocol that mimics textual.Logger."""

    def __call__(self, *args: object, **kwargs: object) -> None:
        """Log a message.

        Args:
            *args (object): Logged directly to the message separated by spaces.
            **kwargs (object): Logged to the message as f"{key}={value!r}", separated by spaces.
        """

    def verbosity(self, *, verbose: bool) -> LoggerProtocol:
        """Get a new logger with selective verbosity.

        Note that unlike when using this method on a Textual logger directly, the type system will enforce that you use
        `verbose` as a keyword argument (not a positional argument). I made this change to address ruff's FBT001 rule.
        Put simply, this requirement makes the calling code easier to read.
        https://docs.astral.sh/ruff/rules/boolean-type-hint-positional-argument/

        Args:
            verbose: True to use HIGH verbosity, otherwise NORMAL.

        Returns:
            New logger.
        """

    @property
    def verbose(self) -> LoggerProtocol:
        """A verbose logger."""

    @property
    def event(self) -> LoggerProtocol:
        """Logs events."""

    @property
    def debug(self) -> LoggerProtocol:
        """Logs debug messages."""

    @property
    def info(self) -> LoggerProtocol:
        """Logs information."""

    @property
    def warning(self) -> LoggerProtocol:
        """Logs warnings."""

    @property
    def error(self) -> LoggerProtocol:
        """Logs errors."""

    @property
    def system(self) -> LoggerProtocol:
        """Logs system information."""

    @property
    def logging(self) -> LoggerProtocol:
        """Logs from stdlib logging module."""

    @property
    def worker(self) -> LoggerProtocol:
        """Logs worker information."""


ResultType = TypeVar("ResultType")


class AppProtocol(Protocol):
    """Protocol for the subset of what the main App can do that the runtime needs."""

    def run_worker(self, work: Awaitable[ResultType], *, thread: bool = False) -> Worker[ResultType]:
        """Run a coroutine in the background.

        See https://textual.textualize.io/guide/workers/.

        Args:
            work (Awaitable[ResultType]): The coroutine to run.
            thread (bool): Mark the worker as a thread worker.
        """

    @property
    def log(self) -> LoggerProtocol:
        """Returns the application logger."""
