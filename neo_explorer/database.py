"""Link NEOs and close approaches and expose them for inspection and querying.

This module defines :class:`NEODatabase`, an in-memory wrapper that stores the
loaded collections, precomputes name/designation indexes, links each close
approach to its NEO (and vice versa), and streams approaches through filters.
No SQL or external storage is involved; plain dictionaries provide O(1) lookup.
"""

from __future__ import annotations

from typing import Iterable, Iterator, Optional

from .filters import FilterStrategy
from .models import CloseApproach, NearEarthObject


class NEODatabase:
    """An in-memory database that links NEOs with their close approaches."""

    def __init__(
        self,
        neos: Iterable[NearEarthObject],
        approaches: Iterable[CloseApproach],
    ) -> None:
        """Create a database and link its NEOs and close approaches.

        :param neos: A collection of :class:`NearEarthObject` instances.
        :param approaches: A collection of :class:`CloseApproach` instances.
        :raises ValueError: If two NEOs share the same primary designation.
        """
        self._neos: tuple[NearEarthObject, ...] = tuple(neos)
        self._approaches: tuple[CloseApproach, ...] = tuple(approaches)
        self._by_designation = self._build_designation_index(self._neos)
        self._by_name = self._build_name_index(self._neos)
        self.link()

    def link(self) -> None:
        """Rebuild the two-way link between NEOs and their close approaches.

        Existing links are cleared first, so calling this repeatedly never
        duplicates approaches. Approaches with no matching NEO keep ``neo=None``
        and are not attached to any object, but remain queryable.
        """
        for neo in self._neos:
            neo.approaches.clear()
        for approach in self._approaches:
            neo = self._by_designation.get(_normalize_designation(approach.designation))
            approach.neo = neo
            if neo is not None:
                neo.approaches.append(approach)

    def get_neo_by_designation(self, designation: str) -> Optional[NearEarthObject]:
        """Return the NEO with the given primary designation, or ``None``."""
        if not designation:
            return None
        return self._by_designation.get(_normalize_designation(designation))

    def get_neo_by_name(self, name: str) -> Optional[NearEarthObject]:
        """Return the NEO with the given IAU name, or ``None``."""
        if not name:
            return None
        return self._by_name.get(_normalize_name(name))

    def query(self, filters: Iterable[FilterStrategy] = ()) -> Iterator[CloseApproach]:
        """Yield close approaches that satisfy every supplied filter.

        :param filters: Filter strategies to apply; an empty collection yields
            every approach.
        :return: A lazy iterator of matching :class:`CloseApproach` instances.
        """
        filters = tuple(filters)
        for approach in self._approaches:
            if all(strategy.matches(approach) for strategy in filters):
                yield approach

    @staticmethod
    def _build_designation_index(neos: tuple[NearEarthObject, ...]) -> dict[str, NearEarthObject]:
        """Index NEOs by designation, rejecting duplicate identifiers."""
        index: dict[str, NearEarthObject] = {}
        for neo in neos:
            key = _normalize_designation(neo.designation)
            if key in index:
                raise ValueError(f"Duplicate NEO designation: {neo.designation!r}")
            index[key] = neo
        return index

    @staticmethod
    def _build_name_index(neos: tuple[NearEarthObject, ...]) -> dict[str, NearEarthObject]:
        """Index named NEOs by name; unnamed NEOs are skipped, first name wins."""
        index: dict[str, NearEarthObject] = {}
        for neo in neos:
            if not neo.name:
                continue
            key = _normalize_name(neo.name)
            index.setdefault(key, neo)
        return index


def _normalize_designation(designation: str) -> str:
    """Normalise a designation for indexing and lookup."""
    return designation.strip()


def _normalize_name(name: str) -> str:
    """Normalise an IAU name for case-insensitive indexing and lookup."""
    return name.strip().casefold()
