from rag_demo.dirs import CONFIG_DIR, DATA_DIR


def test_dirs_created() -> None:
    """Test that the data and config directories exist."""
    assert CONFIG_DIR.is_dir()
    assert DATA_DIR.is_dir()
