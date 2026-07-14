"""Tests for exporting close approaches to CSV and JSON."""

import csv
import json
from datetime import datetime

from neo_explorer.models import CloseApproach, NearEarthObject
from neo_explorer.write import write_to_csv, write_to_json


def _approaches() -> list[CloseApproach]:
    hazardous = NearEarthObject("2020 AB", "Alpha", 0.4, True)
    unknown = NearEarthObject("2099 XX")  # NaN diameter, no name
    return [
        CloseApproach("2020 AB", datetime(2025, 1, 1, 12), 0.02, 18.0, hazardous),
        CloseApproach("2099 XX", datetime(2025, 1, 2, 9), 0.03, 7.0, unknown),
    ]


def test_write_to_csv_uses_empty_string_for_nan_diameter(tmp_path):
    path = tmp_path / "out.csv"
    write_to_csv(_approaches(), path)

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert rows[0]["name"] == "Alpha"
    assert rows[0]["potentially_hazardous"] == "True"
    assert rows[1]["name"] == ""
    assert rows[1]["diameter_km"] == ""


def test_write_to_json_uses_null_for_nan_diameter(tmp_path):
    path = tmp_path / "out.json"
    write_to_json(_approaches(), path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["diameter_km"] == 0.4
    assert data[0]["potentially_hazardous"] is True
    assert data[1]["diameter_km"] is None
    assert data[1]["name"] == ""
