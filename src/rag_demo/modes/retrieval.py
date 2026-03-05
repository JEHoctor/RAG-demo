from pathlib import Path

from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll
from textual.widgets import Footer, Header, Label

from rag_demo.modes._app_types import LogicProviderScreen, LogicProviderWidget


class RetrievalDatabaseScreen(LogicProviderScreen):
    """Manage a single document retrieval database."""

    def compose(self) -> ComposeResult:
        """Create the widgets of the retrieval database screen.

        Returns:
            ComposeResult: composition of the retrieval database screen
        """
        yield Header()
        yield Footer()


class RetrievalDatabaseSummary(LogicProviderWidget):
    """Summary of a single document retrieval database."""

    def compose(self) -> ComposeResult:
        """Create the widgets of the retrieval database summary.

        Returns:
            ComposeResult: composition of the retrieval database summary
        """
        with HorizontalGroup():
            yield Label("Retrieval Database Summary")


class RetrievalScreen(LogicProviderScreen):
    """Manage document retrieval databases."""

    SUB_TITLE = "Retrieval"
    CSS_PATH = Path(__file__).parent / "retrieval.tcss"

    def compose(self) -> ComposeResult:
        """Create the widgets of the retrieval screen.

        Returns:
            ComposeResult: composition of the retrieval screen
        """
        yield Header()
        yield VerticalScroll(id="databases")
        yield Footer()

    def on_mount(self) -> None:
        """Create a dummy retrieval database summary for now."""
        self.query_one("#databases").mount(RetrievalDatabaseSummary())
