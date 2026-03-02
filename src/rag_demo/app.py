from __future__ import annotations

import asyncio
from io import UnsupportedOperation
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, _PrintCapture
from textual.binding import Binding

from rag_demo.modes import ChatScreen, ConfigScreen, HelpScreen

if TYPE_CHECKING:
    from rag_demo.logic import Logic, Runtime


class AppNotMountedError(RuntimeError):
    """Raised when an operation cannot succeed because on_mount() has not been called."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__("This operation cannot succeed because on_mount() has not been called.")


class PrintCaptureHasNoFileDescriptor(UnsupportedOperation):
    """Raised unconditionally when _SafePrintCapture.fileno() is called."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__(
            "Textual is redirecting STDOUT and STDERR with a file object that does not have a file descriptor.",
        )


class _SafePrintCapture(_PrintCapture):
    """Patched capture that correctly signals it has no real file descriptor."""

    def fileno(self) -> int:
        raise PrintCaptureHasNoFileDescriptor


class RAGDemo(App):
    """Main application UI.

    This class is responsible for creating the modes of the application, which are defined in :mod:`rag_demo.modes`.
    """

    TITLE = "RAG Demo"
    CSS_PATH = Path(__file__).parent / "app.tcss"
    BINDINGS: ClassVar = [
        Binding("z", "switch_mode('chat')", "chat"),
        Binding("c", "switch_mode('config')", "configure"),
        Binding("h", "switch_mode('help')", "help"),
    ]
    MODES: ClassVar = {
        "chat": ChatScreen,
        "config": ConfigScreen,
        "help": HelpScreen,
    }

    def __init__(self, logic: Logic) -> None:
        """Initialize the main app.

        Args:
            logic (Logic): Object implementing the application logic.
        """
        super().__init__()
        self._capture_stdout = _SafePrintCapture(self, stderr=False)
        self._capture_stderr = _SafePrintCapture(self, stderr=True)
        self.logic = logic
        self._runtime_future: asyncio.Future[Runtime] | None = None

    async def on_mount(self) -> None:
        """Set the initial mode to chat and initialize async parts of the logic."""
        self.switch_mode("chat")
        # The runtime future must be created in async code so that it is attached to the loop in which it will be used.
        self._runtime_future = asyncio.Future()
        self.run_worker(self._hold_runtime())

    async def _hold_runtime(self) -> None:
        if self._runtime_future is None:
            raise AppNotMountedError
        async with self.logic.runtime(app=self) as runtime:
            self._runtime_future.set_result(runtime)
            # Pause the task until Textual cancels it when the application closes.
            await asyncio.Event().wait()

    async def runtime(self) -> Runtime:
        """Returns the application runtime logic."""
        if self._runtime_future is None:
            raise AppNotMountedError
        return await self._runtime_future
