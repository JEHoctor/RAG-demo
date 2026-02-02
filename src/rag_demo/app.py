from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.app import App
from textual.binding import Binding

from rag_demo.modes import ChatScreen, ConfigScreen, HelpScreen

if TYPE_CHECKING:
    from rag_demo.logic import Logic, Runtime


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
        self.logic = logic
        self._runtime_future: asyncio.Future[Runtime] = asyncio.Future()

    async def on_mount(self) -> None:
        """Set the initial mode to chat and initialize async parts of the logic."""
        self.switch_mode("chat")
        self.run_worker(self._hold_runtime())

    async def _hold_runtime(self) -> None:
        async with self.logic.runtime(app=self) as runtime:
            self._runtime_future.set_result(runtime)
            # Pause the task until Textual cancels it when the application closes.
            await asyncio.Event().wait()

    async def runtime(self) -> Runtime:
        """Returns the application runtime logic."""
        return await self._runtime_future
