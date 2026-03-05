from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.screen import Screen
from textual.widget import Widget

if TYPE_CHECKING:
    from rag_demo.app import RAGDemo


class RAGDemoScreen(Screen):
    """A Screen that provides access to the application logic via its parent app."""

    @property
    def app(self) -> RAGDemo:
        return cast("RAGDemo", super().app)


class RAGDemoWidget(Widget):
    """A Widget that provides access to the application logic via its parent app."""

    @property
    def app(self) -> RAGDemo:
        return cast("RAGDemo", super().app)
