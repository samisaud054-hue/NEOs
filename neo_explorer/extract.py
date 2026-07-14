"""Read NEO and close-approach data from CSV and JSON files.

This module exposes two standalone functions, :func:`load_neos` and
:func:`load_approaches`, that parse the raw NASA/JPL data files and build the
domain models. Only the fields the models need are read; extraneous columns and
JSON fields are ignored and never bound to the constructed objects. Malformed
input raises :class:`ValueError` with the offending line or row for context.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import CloseApproach, NearEarthObject

_TRUE_VALUES = {"y", "yes", "true", "t", "1"}
_DATETIME_FORMATS = ("%Y-%b-%d %H:%M", "%Y-%b-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S")
_REQUIRED_CAD_FIELDS = ("des", "cd", "dist", "v_rel")


def load_neos(path: str | Path) -> tuple[NearEarthObject, ...]:
    """Load near-Earth objects from a CSV file.

    :param path: The path to a CSV file of NEO data (e.g. ``neos.csv``).
    :return: A concrete tuple of :class:`NearEarthObject` instances.
    :raises ValueError: If the ``pdes`` column is missing or a row is invalid.
    """
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or "pdes" not in reader.fieldnames:
            raise ValueError(f"NEO CSV is missing the required 'pdes' column: {reader.fieldnames}")
        neos = []
        for line_number, row in enumerate(reader, start=2):
            try:
                neos.append(
                    NearEarthObject(
                        designation=row["pdes"].strip(),
                        name=_clean_name(row.get("name")),
                        diameter=_to_float_or_nan(row.get("diameter")),
                        hazardous=_to_bool(row.get("pha")),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid NEO on CSV line {line_number}: {exc}") from exc
        return tuple(neos)


def load_approaches(path: str | Path) -> tuple[CloseApproach, ...]:
    """Load close approaches from a JSON file.

    :param path: The path to a JSON file of close-approach data (e.g. ``cad.json``).
    :return: A concrete tuple of :class:`CloseApproach` instances.
    :raises ValueError: If required fields are missing or a data row is invalid.
    """
    with Path(path).open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict) or "fields" not in payload or "data" not in payload:
        raise ValueError("Close-approach JSON must contain 'fields' and 'data' arrays.")
    index = {field: position for position, field in enumerate(payload["fields"])}
    missing = [field for field in _REQUIRED_CAD_FIELDS if field not in index]
    if missing:
        raise ValueError(f"Close-approach JSON is missing fields: {', '.join(missing)}")

    approaches = []
    for row_number, row in enumerate(payload["data"], start=1):
        try:
            approaches.append(
                CloseApproach(
                    designation=str(row[index["des"]]).strip(),
                    time=_to_datetime(str(row[index["cd"]])),
                    distance=float(row[index["dist"]]),
                    velocity=float(row[index["v_rel"]]),
                )
            )
        except (TypeError, ValueError, IndexError) as exc:
            raise ValueError(f"Invalid close approach in JSON row {row_number}: {exc}") from exc
    return tuple(approaches)


def _clean_name(value: Optional[str]) -> Optional[str]:
    """Return a stripped name, or ``None`` when it is missing or empty."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def _to_float_or_nan(value: Optional[str]) -> float:
    """Convert a raw string to a float, using NaN for missing values."""
    if value is None or value.strip() == "":
        return float("nan")
    return float(value)


def _to_bool(value: Optional[str]) -> bool:
    """Interpret a raw string as a boolean flag (missing counts as ``False``)."""
    return value is not None and value.strip().lower() in _TRUE_VALUES


def _to_datetime(value: str) -> datetime:
    """Parse a UTC calendar-date string into a :class:`~datetime.datetime`."""
    value = value.strip()
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date/time format: {value!r}")
