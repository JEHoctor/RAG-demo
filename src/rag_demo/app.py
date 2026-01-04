import time
from pathlib import Path
from typing import ClassVar

from textual.app import App
from textual.binding import Binding

from rag_demo.logic import Logic
from rag_demo.modes import ChatScreen, ConfigScreen, HelpScreen


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

    async def on_mount(self) -> None:
        """Set the initial mode to chat and initialize async parts of the logic."""
        self.log.info("Testing testing 1 2 3")
        self.switch_mode("chat")
        self.run_worker(self.logic.main_worker(self))
        await self.logic.async_init()
        self.log.info(f"Application started in {time.time() - self.logic.application_start_time:.4f}s")
        for name, time_ in self.logic.logic_init_times.items():
            self.log.info(f"{name}: {time_:.4f}s")
