import pytest

from rag_demo.config_mapping import PathMapping


def test_set_and_get_single_level() -> None:
    """A value stored at a depth-1 key is retrievable with the same key."""
    m: PathMapping[str, int] = PathMapping()
    m[("a",)] = 1
    assert m[("a",)] == 1


def test_set_and_get_multi_level() -> None:
    """Shortcuts are created for all intermediate paths so deep keys can be read back."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b", "c")] = 42
    assert m[("a", "b", "c")] == 42


def test_siblings_at_same_depth() -> None:
    """Two keys sharing a parent path are stored independently and do not overwrite each other."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b")] = 1
    m[("a", "c")] = 2
    assert m[("a", "b")] == 1
    assert m[("a", "c")] == 2


def test_overwrite_value_does_not_change_len() -> None:
    """Re-setting an existing key updates the value without counting it as a second insert."""
    m: PathMapping[str, int] = PathMapping()
    m[("a",)] = 1
    m[("a",)] = 99
    assert m[("a",)] == 99
    assert len(m) == 1


def test_len_tracks_inserts() -> None:
    """Only leaf values contribute to len; intermediate nodes created along the way are not counted."""
    m: PathMapping[str, int] = PathMapping()
    assert len(m) == 0
    m[("a",)] = 1
    assert len(m) == 1
    m[("b", "c")] = 2
    assert len(m) == 2


def test_delete_decrements_len() -> None:
    """Deleting a key decrements len so the count stays consistent with the remaining leaves."""
    m: PathMapping[str, int] = PathMapping()
    m[("a",)] = 1
    m[("b",)] = 2
    del m[("a",)]
    assert len(m) == 1


def test_delete_removes_value() -> None:
    """After deletion, accessing the same key raises KeyError."""
    m: PathMapping[str, int] = PathMapping()
    m[("a",)] = 1
    del m[("a",)]
    with pytest.raises(KeyError):
        _ = m[("a",)]


def test_delete_missing_key_raises() -> None:
    """Deleting a key that was never set raises KeyError rather than silently succeeding."""
    m: PathMapping[str, int] = PathMapping()
    with pytest.raises(KeyError):
        del m[("x",)]


def test_delete_intermediate_node_raises() -> None:
    """Deleting a path that points to an intermediate node (not a leaf) raises KeyError."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b")] = 1
    with pytest.raises(KeyError):
        del m[("a",)]


def test_delete_cleans_up_empty_branch() -> None:
    """After deleting the only leaf under a branch, that branch path should be reusable as a leaf."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b")] = 1
    del m[("a", "b")]
    m[("a",)] = 2
    assert m[("a",)] == 2
    assert len(m) == 1


def test_delete_partial_cleanup_leaves_sibling() -> None:
    """Branch cleanup stops at nodes that still have other children, leaving siblings intact."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b")] = 1
    m[("a", "c")] = 2
    del m[("a", "b")]
    assert m[("a", "c")] == 2
    assert len(m) == 1


def test_set_leaf_where_intermediate_dict_exists_raises() -> None:
    """Setting a key whose path is already an intermediate node raises ValueError."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b")] = 1
    with pytest.raises(ValueError, match=r"\('a',\)"):
        m[("a",)] = 2


def test_set_child_where_leaf_exists_raises() -> None:
    """Extending a path through an existing leaf raises ValueError."""
    m: PathMapping[str, int] = PathMapping()
    m[("a",)] = 1
    with pytest.raises(ValueError, match=r"\('a', 'b'\)"):
        m[("a", "b")] = 2


def test_get_missing_key_raises() -> None:
    """Accessing an absent key raises KeyError with the full key, not an internal detail."""
    m: PathMapping[str, int] = PathMapping()
    with pytest.raises(KeyError, match="missing"):
        _ = m[("missing",)]


def test_iter_returns_all_leaf_paths() -> None:
    """Iteration yields full tuple paths to every leaf, skipping intermediate nodes."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b")] = 1
    m[("a", "c")] = 2
    m[("d",)] = 3
    assert set(m) == {("a", "b"), ("a", "c"), ("d",)}


def test_iter_empty_mapping() -> None:
    """Iterating an empty mapping produces no items."""
    m: PathMapping[str, int] = PathMapping()
    assert list(m) == []


def test_convert_returns_nested_dict_with_wrapped_values() -> None:
    """convert() exposes the raw internal structure where leaf values are single-element tuples."""
    m: PathMapping[str, int] = PathMapping()
    m[("a", "b")] = 1
    m[("a", "c")] = 2
    m[("d",)] = 3
    assert m.convert() == {"a": {"b": (1,), "c": (2,)}, "d": (3,)}


def test_mutablemapping_items() -> None:
    """items() returns unwrapped leaf values paired with their full tuple paths."""
    m: PathMapping[str, int] = PathMapping()
    m[("x", "y")] = 10
    m[("z",)] = 20
    assert dict(m.items()) == {("x", "y"): 10, ("z",): 20}
