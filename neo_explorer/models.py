"""Domain models for near-Earth objects and their close approaches.

This module defines the two core entities of the system, :class:`NearEarthObject`
and :class:`CloseApproach`. They are plain data holders: they never read files,
print, or serialise themselves. Each implements ``__str__`` for a human-readable
description. A :class:`CloseApproach` keeps its NEO's primary designation so the
database can link it to the matching :class:`NearEarthObject` after loading.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Optional


class NearEarthObject:
    """A near-Earth object: an asteroid or comet tracked by NASA/JPL."""

    def __init__(
        self,
        designation: str,
        name: Optional[str] = None,
        diameter: float = float("nan"),
        hazardous: bool = False,
    ) -> None:
        """Create a NEO.

        :param designation: The primary designation (a unique identifier).
        :param name: The IAU name, or ``None`` when the NEO is unnamed.
        :param diameter: The diameter in kilometres, or ``float('nan')`` if unknown.
        :param hazardous: Whether the NEO is potentially hazardous.
        """
        self.designation: str = designation
        self.name: Optional[str] = name
        self.diameter: float = diameter
        self.hazardous: bool = hazardous
        self.approaches: list[CloseApproach] = []

    @property
    def fullname(self) -> str:
        """Return a human-readable name combining designation and IAU name."""
        return f"{self.designation} ({self.name})" if self.name else self.designation

    def __str__(self) -> str:
        """Return a readable description of this NEO."""
        size = "an unknown diameter" if math.isnan(self.diameter) else f"a diameter of {self.diameter:.3f} km"
        hazard = "is" if self.hazardous else "is not"
        return f"NEO {self.fullname} has {size} and {hazard} potentially hazardous."

    def __repr__(self) -> str:
        """Return a debugging representation of this NEO."""
        return (
            f"NearEarthObject(designation={self.designation!r}, name={self.name!r}, "
            f"diameter={self.diameter:.3f}, hazardous={self.hazardous!r})"
        )


class CloseApproach:
    """A close approach of a near-Earth object to Earth at a moment in time."""

    def __init__(
        self,
        designation: str,
        time: datetime,
        distance: float,
        velocity: float,
        neo: Optional[NearEarthObject] = None,
    ) -> None:
        """Create a close approach.

        :param designation: The approaching NEO's primary designation; used to
            link this approach to its :class:`NearEarthObject`, and kept afterwards.
        :param time: The moment of closest approach, in UTC.
        :param distance: The nominal approach distance, in astronomical units.
        :param velocity: The relative approach velocity, in kilometres per second.
        :param neo: The linked NEO, or ``None`` until the database links it.
        """
        self.designation: str = designation
        self.time: datetime = time
        self.distance: float = distance
        self.velocity: float = velocity
        self.neo: Optional[NearEarthObject] = neo

    @property
    def date(self) -> date:
        """Return the calendar date of this close approach."""
        return self.time.date()

    def __str__(self) -> str:
        """Return a readable description of this close approach."""
        who = self.neo.fullname if self.neo is not None else self.designation
        return (
            f"On {self.time:%Y-%m-%d %H:%M}, '{who}' approaches Earth at a distance of "
            f"{self.distance:.2f} au and a velocity of {self.velocity:.2f} km/s."
        )

    def __repr__(self) -> str:
        """Return a debugging representation of this close approach."""
        return (
            f"CloseApproach(time={self.time!r}, distance={self.distance:.2f}, "
            f"velocity={self.velocity:.2f}, neo={self.neo!r})"
        )
