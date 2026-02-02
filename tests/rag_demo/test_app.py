from __future__ import annotations

from rag_demo.app import RAGDemo
from rag_demo.logic import Logic, Runtime


async def test_app(logic: Logic) -> None:
    """Test that the app fixture can be created and all components have the correct types."""
    app = RAGDemo(logic=logic)
    async with app.run_test() as test:
        assert isinstance(test.app, RAGDemo)
        assert isinstance(test.app.logic, Logic)
        assert isinstance(await test.app.runtime(), Runtime)
