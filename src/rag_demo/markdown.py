from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline


def soft2hard_break_plugin(md: MarkdownIt) -> None:
    md.inline.ruler2.push("soft2hard_break", _soft2hard_break_plugin)


def _soft2hard_break_plugin(state: StateInline) -> None:
    for token in state.tokens:
        if token.type == "softbreak":
            token.type = "hardbreak"


def parser_factory() -> MarkdownIt:
    """Modified parser that handles newlines according to LLM conventions."""
    return MarkdownIt("gfm-like").use(soft2hard_break_plugin)
