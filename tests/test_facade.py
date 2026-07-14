"""Tests for the NEOExplorerFacade and end-to-end file loading."""

import json

from neo_explorer.facade import NEOExplorerFacade
from neo_explorer.filters import create_filters


def test_search_limit_streams_without_materializing(facade):
    results = facade.search(limit=2)
    assert not isinstance(results, list)
    assert len(list(results)) == 2


def test_search_without_limit_returns_all(facade):
    assert len(list(facade.search())) == 4


def test_get_neo_delegates_to_database(facade):
    assert facade.get_neo_by_name("Alpha").designation == "2020 AB"
    assert facade.get_neo_by_designation("9999 ZZ") is None


def test_from_files_loads_links_and_queries(tmp_path):
    csv_path = tmp_path / "neos.csv"
    csv_path.write_text("pdes,name,diameter,pha\n2020 AB,Alpha,0.4,Y\n", encoding="utf-8")
    json_path = tmp_path / "cad.json"
    json_path.write_text(
        json.dumps(
            {"fields": ["des", "cd", "dist", "v_rel"], "data": [["2020 AB", "2025-Jan-01 12:00", "0.02", "18.5"]]}
        ),
        encoding="utf-8",
    )

    facade = NEOExplorerFacade.from_files(csv_path, json_path)
    results = list(facade.search(create_filters(hazardous=True)))

    assert len(results) == 1
    assert results[0].neo.name == "Alpha"
    assert results[0].velocity == 18.5
