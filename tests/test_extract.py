"""Tests for loading NEOs and close approaches from files."""

import json
import math

from neo_explorer.extract import load_approaches, load_neos


def test_load_neos_converts_types_and_ignores_extra_columns(tmp_path):
    path = tmp_path / "neos.csv"
    path.write_text(
        "id,pdes,name,diameter,pha,extra\n"
        "a0000001,2020 AB,Alpha,0.4,Y,ignored\n"
        "a0000002,2021 CD,,,N,ignored\n",
        encoding="utf-8",
    )

    neos = load_neos(path)

    assert isinstance(neos, tuple)
    assert neos[0].designation == "2020 AB"
    assert neos[0].name == "Alpha"
    assert neos[0].diameter == 0.4
    assert neos[0].hazardous is True
    assert neos[1].name is None
    assert math.isnan(neos[1].diameter)
    assert neos[1].hazardous is False
    assert not hasattr(neos[0], "extra")


def test_load_approaches_reads_only_needed_fields(tmp_path):
    path = tmp_path / "cad.json"
    path.write_text(
        json.dumps(
            {
                "fields": ["des", "orbit_id", "cd", "dist", "v_rel", "h"],
                "data": [["2020 AB", "JPL#1", "2025-Jan-01 12:00", "0.02", "18.5", "22.1"]],
            }
        ),
        encoding="utf-8",
    )

    approaches = load_approaches(path)

    assert isinstance(approaches, tuple)
    assert approaches[0].designation == "2020 AB"
    assert approaches[0].distance == 0.02
    assert approaches[0].velocity == 18.5
    assert approaches[0].time.strftime("%Y-%m-%d %H:%M") == "2025-01-01 12:00"
