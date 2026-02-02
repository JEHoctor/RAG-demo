from __future__ import annotations

from rag_demo.logic import Logic, Runtime


async def test_logic_runtime_initialization(logic: Logic, runtime: Runtime) -> None:
    """Test that the logic and runtime fixtures can be created and have the correct types."""
    assert isinstance(logic, Logic)
    assert isinstance(runtime, Runtime)
