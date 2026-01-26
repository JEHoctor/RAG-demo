from __future__ import annotations

import time
from typing import TYPE_CHECKING, TypeVar

import pytest
import pytest_asyncio

from rag_demo.logic import Logic, Runtime

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable

    from textual.worker import Worker

ResultType = TypeVar("ResultType")


class TestFixtureAppLike:
    """A dummy implementation of App functionality expected by the app logic.

    The logic does not use run_worker via its self.app_like attribute yet. When it does, it will be necessary to
    implement the run_worker method for tests to pass.
    """

    def run_worker(self, work: Awaitable[ResultType]) -> Worker[ResultType]:
        """Run a coroutine in the background.

        See https://textual.textualize.io/guide/workers/.

        Args:
            work (Awaitable[ResultType]): The coroutine to run.
        """
        raise NotImplementedError


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
async def runtime(logic: Logic) -> AsyncIterator[Runtime]:
    """Return a Runtime object suitable for use in tests."""
    async with logic.runtime(app_like=TestFixtureAppLike()) as runtime:
        yield runtime


@pytest.mark.asyncio
async def test_logic_runtime_initialization(logic: Logic, runtime: Runtime) -> None:
    """Test that the logic and runtime fixtures can be created and have the correct types."""
    assert isinstance(logic, Logic)
    assert isinstance(runtime, Runtime)
