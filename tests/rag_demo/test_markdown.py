from markdown_it import MarkdownIt
from markdown_it.token import Token

from rag_demo import markdown

SAMPLE_MARKDOWN = """
Here's a haiku about snakes:

Silent scales gliding,
Through tall grass, a ribbon flows—
Sun-warmed stone awaits.
"""


def test_parser_removes_softbreaks() -> None:
    """Test that our parser and a generic parser differ only in producing hardbreak and softbreak tokens respectively."""
    parser = markdown.parser_factory()
    assert isinstance(parser, MarkdownIt)
    comparison_parser = MarkdownIt("gfm-like")

    result = parser.parse(SAMPLE_MARKDOWN)
    comparison_result = comparison_parser.parse(SAMPLE_MARKDOWN)

    assert isinstance(result, list)
    assert isinstance(comparison_result, list)
    assert all([isinstance(item, Token) for item in result])
    assert all([isinstance(item, Token) for item in comparison_result])

    # Traverse the token tree using an explicit stack instead of recursion.
    # This makes it simpler for all checks to be asserts.
    stack: list[tuple[list[Token], list[Token], int]] = [(result, comparison_result, 0)]

    comparisons = 0
    while stack:
        result, comparison_result, index = stack.pop()
        if index == 0:
            assert len(result) == len(comparison_result)
        if index == len(result):
            continue
        result_token = result[index]
        comparison_result_token = comparison_result[index]
        stack.append((result, comparison_result, index + 1))
        if result_token.children is not None or comparison_result_token.children is not None:
            assert result_token.children is not None
            assert comparison_result_token.children is not None
            stack.append((result_token.children, comparison_result_token.children, 0))
            result_token.children = None
            comparison_result_token.children = None
        if comparison_result_token.type == "softbreak":
            comparison_result_token.type = "hardbreak"
        assert result_token == comparison_result_token
        comparisons += 1

    assert comparisons == 12
