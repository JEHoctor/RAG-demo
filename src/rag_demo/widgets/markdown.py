from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from textual.widgets import Markdown as BaseMarkdown


def _soft2hard_break_plugin(md: MarkdownIt) -> None:
    md.inline.ruler2.push("soft2hard_break", _soft2hard_break)


def _soft2hard_break(state: StateInline) -> None:
    for token in state.tokens:
        if token.type == "softbreak":
            token.type = "hardbreak"


def parser_factory() -> MarkdownIt:
    """Modified parser that handles newlines according to LLM conventions."""
    return MarkdownIt("gfm-like").use(_soft2hard_break_plugin)


class Markdown(BaseMarkdown):
    """A Textual Markdown widget with a custom markdown parser that converts soft breaks to hard breaks to match LLM conventions."""

    def __init__(
        self,
        markdown: str | None = None,
        *,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        open_links: bool = True,
    ) -> None:
        """A Markdown widget.

        Args:
            markdown: String containing Markdown or None to leave blank for now.
            name: The name of the widget.
            id: The ID of the widget in the DOM.
            classes: The CSS classes of the widget.
            open_links: Open links automatically. If you set this to `False`, you can handle the [`LinkClicked`][textual.widgets.markdown.Markdown.LinkClicked] events.
        """
        super().__init__(
            markdown=markdown,
            name=name,
            id=id,
            classes=classes,
            parser_factory=parser_factory,
            open_links=open_links,
        )
