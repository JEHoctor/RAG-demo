from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import Footer, Header, Label

from rag_demo.modes._rag_demo_screen import RAGDemoScreen


class HelpScreen(RAGDemoScreen):
    """Display information about the application."""

    SUB_TITLE = "Help"
    CSS_PATH = Path(__file__).parent / "help.tcss"

    def compose(self) -> ComposeResult:
        """Create the widgets of the help screen.

        Returns:
            ComposeResult: composition of the help screen

        Yields:
            Iterator[ComposeResult]: composition of the help screen
        """
        yield Header()
        yield Label("Help Screen (under construction)")
        yield Footer()
