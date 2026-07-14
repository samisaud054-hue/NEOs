"""Tests for the domain models."""

import math
from datetime import datetime

from neo_explorer.models import CloseApproach, NearEarthObject


def test_neo_defaults_are_rubric_compliant():
    neo = NearEarthObject("2020 AB")
    assert neo.name is None
    assert math.isnan(neo.diameter)
    assert neo.hazardous is False
    assert neo.approaches == []


def test_neo_approaches_are_independent_per_instance():
    a, b = NearEarthObject("A"), NearEarthObject("B")
    a.approaches.append("x")
    assert b.approaches == []


def test_neo_str_handles_missing_name_and_nan_diameter():
    text = str(NearEarthObject("2022 EF"))
    assert "2022 EF" in text
    assert "unknown diameter" in text


def test_close_approach_keeps_designation_and_defaults_neo_none():
    approach = CloseApproach("2020 AB", datetime(2025, 1, 1, 12), 0.02, 18.0)
    assert approach.designation == "2020 AB"
    assert approach.neo is None
    assert approach.date.isoformat() == "2025-01-01"


def test_close_approach_str_without_linked_neo():
    text = str(CloseApproach("2020 AB", datetime(2025, 1, 1, 12), 0.02, 18.0))
    assert "2020 AB" in text
