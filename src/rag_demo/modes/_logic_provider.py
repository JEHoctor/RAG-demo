from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from textual.screen import Screen
from textual.widget import Widget

if TYPE_CHECKING:
    from rag_demo.logic import Logic, Runtime


class LogicProvider(Protocol):
    """ABC for classes that contain application logic."""

    logic: Logic

    async def runtime(self) -> Runtime: ...


class LogicProviderScreen(Screen):
    """A Screen that provides access to the application logic via its parent app."""

    @property
    def logic(self) -> Logic:
        """Returns the application logic of the parent app."""
        return cast("LogicProvider", self.app).logic

    async def runtime(self) -> Runtime:
        """Returns the application runtime of the parent app."""
        return await cast("LogicProvider", self.app).runtime()


class LogicProviderWidget(Widget):
    """A Widget that provides access to the application logic via its parent app."""

    @property
    def logic(self) -> Logic:
        """Returns the application logic of the parent app."""
        return cast("LogicProvider", self.app).logic

    async def runtime(self) -> Runtime:
        """Returns the application runtime of the parent app."""
        return await cast("LogicProvider", self.app).runtime()
