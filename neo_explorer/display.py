"""Format NEOs and close approaches for the console.

These standalone functions render domain objects as human-readable text and
print them. They keep presentation concerns out of the database and facade.
"""

from __future__ import annotations

from typing import Iterable

from .models import CloseApproach, NearEarthObject


def print_approaches(approaches: Iterable[CloseApproach]) -> None:
    """Print a stream of close approaches, or a notice when there are none."""
    count = 0
    for approach in approaches:
        print(approach)
        count += 1
    if count == 0:
        print("No matching close approaches found.")


def print_neo(neo: NearEarthObject) -> None:
    """Print a NEO followed by the count of its known close approaches."""
    print(neo)
    print(f"Known close approaches: {len(neo.approaches)}")
