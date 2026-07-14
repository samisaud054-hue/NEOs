"""Shared fixtures: a small, hand-built database of NEOs and approaches."""

from datetime import datetime

import pytest

from neo_explorer.database import NEODatabase
from neo_explorer.facade import NEOExplorerFacade
from neo_explorer.models import CloseApproach, NearEarthObject


@pytest.fixture
def neos() -> list[NearEarthObject]:
    return [
        NearEarthObject("2020 AB", "Alpha", 0.4, True),
        NearEarthObject("2021 CD", None, 0.1, False),
        NearEarthObject("2022 EF", None, float("nan"), False),
    ]


@pytest.fixture
def approaches() -> list[CloseApproach]:
    return [
        CloseApproach("2020 AB", datetime(2025, 1, 1, 12), 0.02, 18.0),
        CloseApproach("2021 CD", datetime(2025, 1, 1, 18), 0.05, 10.0),
        CloseApproach("2022 EF", datetime(2025, 1, 2, 9), 0.01, 25.0),
        CloseApproach("9999 ZZ", datetime(2025, 1, 3, 0), 0.10, 5.0),  # orphan
    ]


@pytest.fixture
def database(neos, approaches) -> NEODatabase:
    return NEODatabase(neos, approaches)


@pytest.fixture
def facade(database) -> NEOExplorerFacade:
    return NEOExplorerFacade(database)
