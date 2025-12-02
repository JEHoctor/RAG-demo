from rag_demo import rag


def test_llm_has_astream() -> None:
    assert hasattr(rag.llm, "astream")
    assert callable(rag.llm.astream)
