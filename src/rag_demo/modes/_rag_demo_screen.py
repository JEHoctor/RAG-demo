from typing import Protocol, cast

from textual.screen import Screen

from rag_demo.logic import Logic


class AppLogicProvider(Protocol):
    """ABC for classes that contain application logic."""

    logic: Logic


class RAGDemoScreen(Screen):
    """A Screen for RAGDemo that knows that the app is an AppLogicProvider."""

    @property
    def logic(self) -> Logic:
        """Satisfy the type checker by attesting that the app is an AppLogicProvider.

        Returns:
            Logic: The application logic of the parent app
        """
        return cast("AppLogicProvider", self.app).logic
