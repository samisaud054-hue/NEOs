"""Write streams of close approaches to CSV or JSON files.

These standalone functions serialise close approaches for export. They do not
filter, format for the console, or hold state; each simply consumes an iterable
of approaches and writes it to disk in the requested format.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable

from .models import CloseApproach

_FIELDNAMES = (
    "datetime_utc",
    "distance_au",
    "velocity_km_s",
    "designation",
    "name",
    "diameter_km",
    "potentially_hazardous",
)


def write_to_csv(approaches: Iterable[CloseApproach], path: str | Path) -> None:
    """Write close approaches to a CSV file with a fixed set of columns.

    :param approaches: The approaches to write.
    :param path: The destination CSV file path.
    """
    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for approach in approaches:
            writer.writerow(_serialize(approach, nan_diameter=""))


def write_to_json(approaches: Iterable[CloseApproach], path: str | Path) -> None:
    """Write close approaches to a JSON file as a list of objects.

    :param approaches: The approaches to write.
    :param path: The destination JSON file path.
    """
    rows = [_serialize(approach, nan_diameter=None) for approach in approaches]
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(rows, file, indent=2, ensure_ascii=False)


def _serialize(approach: CloseApproach, *, nan_diameter: object) -> dict[str, object]:
    """Build a flat, serialisable record for a single close approach.

    :param nan_diameter: The value to emit when the NEO's diameter is unknown
        (an empty string for CSV, ``None`` for JSON).
    """
    neo = approach.neo
    diameter = neo.diameter if neo is not None else float("nan")
    return {
        "datetime_utc": approach.time.strftime("%Y-%m-%d %H:%M"),
        "distance_au": approach.distance,
        "velocity_km_s": approach.velocity,
        "designation": neo.designation if neo is not None else approach.designation,
        "name": (neo.name if neo is not None and neo.name else ""),
        "diameter_km": nan_diameter if math.isnan(diameter) else diameter,
        "potentially_hazardous": bool(neo.hazardous) if neo is not None else False,
    }
