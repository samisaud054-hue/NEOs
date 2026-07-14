"""Tests for the Strategy-based filtering system."""

from datetime import date, datetime

from neo_explorer.filters import (
    HazardousFilter,
    MaxDistanceFilter,
    MinDiameterFilter,
    create_filters,
)
from neo_explorer.models import CloseApproach, NearEarthObject


def _designations(approaches):
    return [a.neo.designation if a.neo else a.designation for a in approaches]


def test_combined_filters_apply_conjunctively(database):
    filters = create_filters(start_date=date(2025, 1, 1), end_date=date(2025, 1, 1), hazardous=True)
    assert _designations(database.query(filters)) == ["2020 AB"]


def test_distance_and_velocity(database):
    filters = create_filters(distance_max=0.02, velocity_min=20)
    assert _designations(database.query(filters)) == ["2022 EF"]


def test_diameter_filter_excludes_unknown_diameter(database):
    # 2022 EF has NaN diameter; the orphan 9999 ZZ has neo=None.
    assert _designations(database.query([MinDiameterFilter(0.2)])) == ["2020 AB"]


def test_nan_diameter_does_not_match_any_bound():
    approach = CloseApproach("X", datetime(2025, 1, 1), 0.01, 5.0, NearEarthObject("X"))
    assert MinDiameterFilter(0.0).matches(approach) is False


def test_hazardous_filter_survives_missing_neo():
    orphan = CloseApproach("Z", datetime(2025, 1, 1), 0.01, 5.0, None)
    assert HazardousFilter(True).matches(orphan) is False


def test_create_filters_empty_by_default():
    assert create_filters() == []


def test_max_distance_boundary_is_inclusive():
    approach = CloseApproach("X", datetime(2025, 1, 1), 0.05, 5.0, NearEarthObject("X"))
    assert MaxDistanceFilter(0.05).matches(approach) is True
