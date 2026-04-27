from __future__ import annotations

from io import UnsupportedOperation
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, _PrintCapture
from textual.binding import Binding

from rag_demo.modes import ChatScreen, ConfigScreen, HelpScreen, RetrievalScreen

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from rag_demo.logic import Logic, Runtime


class AppNotMountedError(RuntimeError):
    """Raised when an operation cannot succeed because the app is not mounted."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__("This operation cannot succeed because the app is not mounted.")


class MisbehavingRuntimeLifecycleManagerError(RuntimeError):
    """Raised when cleaning up the runtime lifecycle manager fails."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__("The runtime lifecycle manager yielded when StopAsyncIteration was expected.")


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
        Binding("r", "switch_mode('retrieval')", "retrieval"),
        Binding("h", "switch_mode('help')", "help"),
    ]
    MODES: ClassVar = {
        "chat": ChatScreen,
        "config": ConfigScreen,
        "retrieval": RetrievalScreen,
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
        self._runtime: Runtime | None = None
        self._runtime_lifecycle_manager: AsyncIterator[Runtime] | None = None

    async def on_mount(self) -> None:
        """Set the initial mode to chat and initialize async parts of the logic."""
        self.switch_mode("chat")
        manager = self._new_runtime_lifecycle_manager()
        runtime = await anext(manager)
        self._runtime_lifecycle_manager = manager
        self._runtime = runtime

    async def on_unmount(self) -> None:
        """Clean up the application runtime."""
        if self._runtime_lifecycle_manager is None:
            raise AppNotMountedError
        manager = self._runtime_lifecycle_manager
        self._runtime = None
        self._runtime_lifecycle_manager = None
        try:
            await anext(manager)
        except StopAsyncIteration:
            pass
        else:
            raise MisbehavingRuntimeLifecycleManagerError

    async def _new_runtime_lifecycle_manager(self) -> AsyncIterator[Runtime]:
        async with self.logic.runtime(app=self) as runtime:
            yield runtime

    @property
    def runtime(self) -> Runtime:
        """Returns the application runtime logic."""
        if self._runtime is None:
            raise AppNotMountedError
        return self._runtime
