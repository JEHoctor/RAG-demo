from typing import Protocol, cast

from textual.screen import Screen
from textual.widget import Widget

from rag_demo.logic import Logic


class LogicProvider(Protocol):
    """ABC for classes that contain application logic."""

    logic: Logic


class LogicProviderScreen(Screen):
    """A Screen that provides access to the application logic via its parent app."""

    @property
    def logic(self) -> Logic:
        """The application logic of the parent app.

        Returns:
            Logic: The application logic of the parent app.
        """
        # Satisfy the type checker by attesting that the app is an AppLogicProvider.
        return cast("LogicProvider", self.app).logic


class LogicProviderWidget(Widget):
    """A Widget that provides access to the application logic via its parent app."""

    @property
    def logic(self) -> Logic:
        """The application logic of the parent app.

        Returns:
            Logic: The application logic of the parent app.
        """
        # Satisfy the type checker by attesting that the app is an AppLogicProvider.
        return cast("LogicProvider", self.app).logic
