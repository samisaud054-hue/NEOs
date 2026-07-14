"""A thin facade that unifies the system behind one small API for the CLI.

:class:`NEOExplorerFacade` is the single entry point the command-line interface
talks to. It coordinates extraction, the database, and the filtering system, but
delegates all real work to them: it contains no parsing, linking, filtering, or
formatting logic of its own. The small API and clear responsibility boundaries
keep the risk of it becoming a God Object low.
"""

from __future__ import annotations

from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator, Optional

from . import extract
from .database import NEODatabase
from .filters import FilterStrategy
from .models import CloseApproach, NearEarthObject


class NEOExplorerFacade:
    """Unified access point to load, inspect, and query NEO close approaches."""

    def __init__(self, database: NEODatabase) -> None:
        """Wrap an already-constructed :class:`NEODatabase`.

        :param database: The linked database of NEOs and close approaches.
        """
        self._database = database

    @classmethod
    def from_files(cls, neos_path: str | Path, approaches_path: str | Path) -> "NEOExplorerFacade":
        """Build a facade by loading NEOs and approaches from data files.

        :param neos_path: Path to the NEO CSV file.
        :param approaches_path: Path to the close-approach JSON file.
        :return: A ready-to-use :class:`NEOExplorerFacade`.
        """
        neos = extract.load_neos(neos_path)
        approaches = extract.load_approaches(approaches_path)
        return cls(NEODatabase(neos, approaches))

    def get_neo_by_designation(self, designation: str) -> Optional[NearEarthObject]:
        """Return the NEO with the given primary designation, or ``None``."""
        return self._database.get_neo_by_designation(designation)

    def get_neo_by_name(self, name: str) -> Optional[NearEarthObject]:
        """Return the NEO with the given IAU name, or ``None``."""
        return self._database.get_neo_by_name(name)

    def search(
        self,
        filters: Iterable[FilterStrategy] = (),
        limit: Optional[int] = None,
    ) -> Iterator[CloseApproach]:
        """Stream close approaches matching every filter, optionally limited.

        :param filters: Filter strategies to apply; empty matches everything.
        :param limit: Maximum number of results to yield, or ``None`` for all.
        :return: A lazy iterator of matching :class:`CloseApproach` instances.
        """
        results = self._database.query(filters)
        if limit is not None and limit > 0:
            return islice(results, limit)
        return results
