from rag_demo import main


def test_main_returns_none() -> None:
    assert main() is None  # type: ignore[func-returns-value]
