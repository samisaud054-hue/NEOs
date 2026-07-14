"""Tests for the NEODatabase: indexing, linking, normalization, policies."""


import pytest

from neo_explorer.database import NEODatabase
from neo_explorer.models import NearEarthObject


def test_links_neo_to_approaches_both_ways(database):
    neo = database.get_neo_by_designation("2020 AB")
    assert [a.designation for a in neo.approaches] == ["2020 AB"]
    assert neo.approaches[0].neo is neo


def test_lookup_is_normalized(database):
    assert database.get_neo_by_designation("  2020 AB  ") is not None
    assert database.get_neo_by_name("ALPHA") is not None
    assert database.get_neo_by_name("alpha") is database.get_neo_by_designation("2020 AB")


def test_orphan_approach_is_kept_but_unlinked(database):
    orphans = [a for a in database.query() if a.neo is None]
    assert [a.designation for a in orphans] == ["9999 ZZ"]


def test_duplicate_designation_raises():
    neos = [NearEarthObject("2020 AB"), NearEarthObject(" 2020 AB ")]
    with pytest.raises(ValueError, match="Duplicate NEO designation"):
        NEODatabase(neos, [])


def test_duplicate_name_first_wins():
    first = NearEarthObject("A1", "Twin")
    second = NearEarthObject("A2", "twin")
    database = NEODatabase([first, second], [])
    assert database.get_neo_by_name("TWIN") is first


def test_relinking_does_not_duplicate_approaches(database):
    database.link()
    database.link()
    neo = database.get_neo_by_designation("2020 AB")
    assert len(neo.approaches) == 1


def test_query_streams_lazily(database):
    results = database.query()
    assert next(results) is not None  # a generator, not a materialised list


def test_empty_name_is_not_indexed():
    database = NEODatabase([NearEarthObject("A1", None)], [])
    assert database.get_neo_by_name("") is None
