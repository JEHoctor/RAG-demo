from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


type NestedDict[K, V] = dict[K, NestedDict[K, V] | V]
type NestedMapping[K, V] = Mapping[K, NestedMapping[K, V] | V]


class PathMapping[KE, V](MutableMapping[tuple[KE, ...], V]):
    """A hierarchical mapping that can be updated with tuple keys and converted to nested dictionaries."""

    def __init__(self) -> None:
        """Initialize the path mapping."""
        # The underlying data structure is a nested dictionary, but we only track a mapping of shortcuts
        # into this data structure. For every dictionary in the nested structure we maintain a shortcut.
        self._shortcuts: dict[tuple[KE, ...], NestedDict[KE, tuple[V]]] = {(): {}}
        self._len = 0

    def __getitem__(self, key: tuple[KE, ...]) -> V:
        """Return an item from a path of key elements."""
        branch: tuple[KE, ...] = key[:-1]
        leaf: KE = key[-1]
        result = self._shortcuts[branch][leaf]
        if isinstance(result, dict):
            raise KeyError
        return result[0]

    def __setitem__(self, key: tuple[KE, ...], value: V) -> None:
        """Set an item in a path of key elements."""
        branch: tuple[KE, ...] = key[:-1]
        leaf: KE = key[-1]
        spoke: list[KE] = []
        while branch not in self._shortcuts:
            spoke.append(branch[-1])
            branch: tuple[KE, ...] = branch[:-1]
        landing: NestedDict[KE, tuple[V]] = self._shortcuts[branch]
        while spoke:
            segment: KE = spoke.pop()
            if segment in landing:
                raise KeyError
            new_nested_dict: NestedDict[KE, tuple[V]] = {}
            landing[segment] = new_nested_dict
            branch: tuple[KE, ...] = (*branch, segment)
            self._shortcuts[branch] = new_nested_dict
            landing = new_nested_dict
        if isinstance(landing.get(leaf), dict):
            raise KeyError
        if leaf not in landing:
            self._len += 1
        landing[leaf] = (value,)

    def __delitem__(self, key: tuple[KE, ...]) -> None:
        """Delete an item from a path of key elements."""
        branch: tuple[KE, ...] = key[:-1]
        leaf: KE = key[-1]
        if leaf not in self._shortcuts[branch]:
            raise KeyError
        del self._shortcuts[branch][leaf]

    def __iter__(self) -> Iterator[tuple[KE, ...]]:
        """Return an iterator over the keys of the mapping."""
        for branch, landing in self._shortcuts.items():
            for key, value in landing.items():
                if not isinstance(value, dict):
                    yield (*branch, key)

    def __len__(self) -> int:
        """Return the number of items in the mapping."""
        return self._len

    def convert(self) -> NestedMapping[KE, tuple[V]]:
        """Return the underlying nested dictionary as a read-only view of the mapping."""
        return self._shortcuts[()]
