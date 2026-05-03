from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping


type NestedDict[K, V] = dict[K, NestedDict[K, V] | V]
type NestedMapping[K, V] = Mapping[K, NestedMapping[K, V] | V]


class TreeMapping[KE, V](MutableMapping[tuple[KE, ...], V]):
    """A hierarchical mapping that can be updated with tuple keys and converted to nested dictionaries."""

    def __init__(self) -> None:
        """Initialize the tree mapping."""
        # The underlying data structure is a nested dictionary, but we only track a mapping of shortcuts
        # into this data structure. For every dictionary in the nested structure we maintain a shortcut.
        self._shortcuts: dict[tuple[KE, ...], NestedDict[KE, V]] = {(): {}}
        self._len = 0

    def __getitem__(self, key: tuple[KE, ...]) -> V:
        """Return an item from a path of key elements."""
        if key in self._shortcuts:
            raise KeyError(key)
        branch: tuple[KE, ...] = key[:-1]
        if branch not in self._shortcuts:
            raise KeyError(key)
        leaf: KE = key[-1]
        if leaf not in self._shortcuts[branch]:
            raise KeyError(key)
        # Type checker can't reason about the shortcuts invariant:
        return cast("V", self._shortcuts[branch][leaf])

    def __setitem__(self, key: tuple[KE, ...], value: V) -> None:
        """Set an item in a path of key elements."""
        if key in self._shortcuts:
            raise ValueError(key)
        branch: tuple[KE, ...] = key[:-1]
        leaf: KE = key[-1]
        stack: list[tuple[KE, tuple[KE, ...]]] = []
        while branch not in self._shortcuts:
            stack.append((branch[-1], branch))
            branch: tuple[KE, ...] = branch[:-1]
        landing: NestedDict[KE, V] = self._shortcuts[branch]
        while stack:
            segment, branch = stack.pop()
            if segment in landing:
                raise ValueError(key)
            new_nested_dict: NestedDict[KE, V] = {}
            landing[segment] = new_nested_dict
            self._shortcuts[branch] = new_nested_dict
            landing = new_nested_dict
        if leaf not in landing:
            self._len += 1
        landing[leaf] = value

    def __delitem__(self, key: tuple[KE, ...]) -> None:
        """Delete an item from a path of key elements."""
        if key in self._shortcuts:
            raise KeyError(key)
        branch: tuple[KE, ...] = key[:-1]
        if branch not in self._shortcuts:
            raise KeyError(key)
        leaf: KE = key[-1]
        if leaf not in self._shortcuts[branch]:
            raise KeyError(key)
        del self._shortcuts[branch][leaf]
        self._len -= 1
        # Clean up empty intermediate dicts so their paths can be reused as leaves.
        while branch and not self._shortcuts[branch]:
            del self._shortcuts[branch]
            parent = branch[:-1]
            del self._shortcuts[parent][branch[-1]]
            branch = parent

    def __iter__(self) -> Iterator[tuple[KE, ...]]:
        """Return an iterator over the keys of the mapping."""
        for branch, landing in self._shortcuts.items():
            for leaf in landing:
                path: tuple[KE, ...] = (*branch, leaf)
                if path not in self._shortcuts:
                    yield path

    def __len__(self) -> int:
        """Return the number of items in the mapping."""
        return self._len

    def convert(self) -> NestedMapping[KE, V]:
        """Return the underlying nested dictionary as a read-only view of the mapping."""
        return self._shortcuts[()]
