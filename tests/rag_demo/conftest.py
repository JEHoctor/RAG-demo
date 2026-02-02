from __future__ import annotations

import time
from typing import TYPE_CHECKING, TypeVar

import pytest
import pytest_asyncio

from rag_demo.logic import Logic

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Sequence

    from textual.worker import Worker

    from rag_demo.app_protocol import AppProtocol, LoggerProtocol
    from rag_demo.logic import Runtime

type LogGroup = str
type LogVerbosity = str
type LogRecord = tuple[LogGroup, LogVerbosity, tuple[object, ...], dict[str, object], str]


class LoggerFixture:
    """Logger fixture that just records logging calls in a list for later inspection."""

    def __init__(
        self,
        *,
        group: LogGroup = "info",
        verbosity: LogVerbosity = "normal",
    ) -> None:
        """Initialize the logging fixture.

        Args:
            group (str, optional): Logging group such as "event", "debug", or "warning". Defaults to "info".
            verbosity (str, optional): Verbosity is either "high" or "normal". Defaults to "normal".
        """
        self._group = group
        self._verbosity = verbosity

        self._log: list[LogRecord] = []

    @property
    def log(self) -> Sequence[LogRecord]:
        """Return the recorded logging calls.

        Note that the return type is Sequence, not list or MutableSequence. This protects the internal _log attribute
        from modification.
        """
        return self._log

    def __from_self(self, *, group: LogGroup, verbosity: LogVerbosity) -> LoggerFixture:
        """Create a new LoggerFixture with the same underlying list of log records as this one."""
        lf = LoggerFixture(group=group, verbosity=verbosity)
        lf._log = self._log
        return lf

    def __call__(self, *args: object, **kwargs: object) -> None:
        """Log a message.

        Args:
            *args (object): Logged directly to the message separated by spaces.
            **kwargs (object): Logged to the message as f"{key}={value!r}", separated by spaces.
        """
        # This code block is from `textual/__init__.py`.
        output = " ".join(str(arg) for arg in args)
        if kwargs:
            key_values = " ".join(f"{key}={value!r}" for key, value in kwargs.items())
            output = f"{output} {key_values}" if output else key_values
        # End of code block from `textual/__init__.py`.`
        self._log.append((self._group, self._verbosity, args, kwargs, output))

    def verbosity(self, *, verbose: bool) -> LoggerFixture:
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
        return self.__from_self(group=self._group, verbosity="high" if verbose else "normal")

    @property
    def verbose(self) -> LoggerFixture:
        """A verbose logger."""
        return self.__from_self(group=self._group, verbosity="high")

    @property
    def event(self) -> LoggerFixture:
        """Logs events."""
        return self.__from_self(group="event", verbosity="normal")

    @property
    def debug(self) -> LoggerFixture:
        """Logs debug messages."""
        return self.__from_self(group="debug", verbosity="normal")

    @property
    def info(self) -> LoggerFixture:
        """Logs information."""
        return self.__from_self(group="info", verbosity="normal")

    @property
    def warning(self) -> LoggerFixture:
        """Logs warnings."""
        return self.__from_self(group="warning", verbosity="normal")

    @property
    def error(self) -> LoggerFixture:
        """Logs errors."""
        return self.__from_self(group="error", verbosity="normal")

    @property
    def system(self) -> LoggerFixture:
        """Logs system information."""
        return self.__from_self(group="system", verbosity="normal")

    @property
    def logging(self) -> LoggerFixture:
        """Logs from stdlib logging module."""
        return self.__from_self(group="logging", verbosity="normal")

    @property
    def worker(self) -> LoggerFixture:
        """Logs worker information."""
        return self.__from_self(group="worker", verbosity="normal")


_: LoggerProtocol = LoggerFixture()


ResultType = TypeVar("ResultType")


class AppFixture:
    """App fixture that uses LoggerFixture for logging and simulates the Textual Worker system."""

    def __init__(self) -> None:
        """Initialize the app fixture."""
        self._log = LoggerFixture()

    def run_worker(self, work: Awaitable[ResultType], *, thread: bool = False) -> Worker[ResultType]:
        """Run a coroutine in the background."""
        raise NotImplementedError

    @property
    def log(self) -> LoggerFixture:
        """Returns the logger fixture."""
        return self._log


_: AppProtocol = AppFixture()


@pytest.fixture
def app() -> AppFixture:
    """Return an app fixture."""
    return AppFixture()


@pytest.fixture
def logic() -> Logic:
    """Return a Logic object suitable for use in tests.

    The applications databases are in-memory.
    """
    return Logic(
        username="test-user",
        application_start_time=time.time() - 3.0,
        checkpoints_sqlite_db=":memory:",
        app_sqlite_db=":memory:",
    )


@pytest_asyncio.fixture
async def runtime(logic: Logic, app: AppFixture) -> AsyncIterator[Runtime]:
    """Return a Runtime object suitable for use in tests."""
    async with logic.runtime(app=app) as runtime:
        yield runtime
