"""A Strategy-based filtering system for close approaches.

Each user criterion is a small, explicit strategy that implements the
:class:`FilterStrategy` protocol: a single ``matches`` method returning whether
an approach satisfies it. :func:`create_filters` assembles a list of strategies
from user input, and the database composes them with ``all(...)`` so any number
of criteria combine without branching logic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Optional, Protocol

from .models import CloseApproach


class FilterStrategy(Protocol):
    """A single close-approach filtering criterion."""

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether ``approach`` satisfies this criterion."""
        ...


@dataclass(frozen=True)
class DateFilter:
    """Match approaches occurring on an exact calendar date."""

    on: date

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the approach happens on the target date."""
        return approach.date == self.on


@dataclass(frozen=True)
class StartDateFilter:
    """Match approaches occurring on or after a start date."""

    start: date

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the approach happens on or after the start date."""
        return approach.date >= self.start


@dataclass(frozen=True)
class EndDateFilter:
    """Match approaches occurring on or before an end date."""

    end: date

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the approach happens on or before the end date."""
        return approach.date <= self.end


@dataclass(frozen=True)
class MinDistanceFilter:
    """Match approaches at least a minimum distance away."""

    minimum: float

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the approach distance is at least the minimum."""
        return approach.distance >= self.minimum


@dataclass(frozen=True)
class MaxDistanceFilter:
    """Match approaches no farther than a maximum distance."""

    maximum: float

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the approach distance is at most the maximum."""
        return approach.distance <= self.maximum


@dataclass(frozen=True)
class MinVelocityFilter:
    """Match approaches at least a minimum relative velocity."""

    minimum: float

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the approach velocity is at least the minimum."""
        return approach.velocity >= self.minimum


@dataclass(frozen=True)
class MaxVelocityFilter:
    """Match approaches no faster than a maximum relative velocity."""

    maximum: float

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the approach velocity is at most the maximum."""
        return approach.velocity <= self.maximum


@dataclass(frozen=True)
class MinDiameterFilter:
    """Match approaches whose NEO is at least a minimum diameter."""

    minimum: float

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the NEO diameter is known and at least the minimum."""
        diameter = _diameter_or_nan(approach)
        return not math.isnan(diameter) and diameter >= self.minimum


@dataclass(frozen=True)
class MaxDiameterFilter:
    """Match approaches whose NEO is no larger than a maximum diameter."""

    maximum: float

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the NEO diameter is known and at most the maximum."""
        diameter = _diameter_or_nan(approach)
        return not math.isnan(diameter) and diameter <= self.maximum


@dataclass(frozen=True)
class HazardousFilter:
    """Match approaches by their NEO's potentially-hazardous flag."""

    hazardous: bool

    def matches(self, approach: CloseApproach) -> bool:
        """Return whether the NEO's hazard flag equals the target."""
        if approach.neo is None:
            return False
        return approach.neo.hazardous == self.hazardous


def create_filters(
    *,
    date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    distance_min: Optional[float] = None,
    distance_max: Optional[float] = None,
    velocity_min: Optional[float] = None,
    velocity_max: Optional[float] = None,
    diameter_min: Optional[float] = None,
    diameter_max: Optional[float] = None,
    hazardous: Optional[bool] = None,
) -> list[FilterStrategy]:
    """Build a list of filter strategies from user-specified criteria.

    Only criteria that are not ``None`` produce a strategy, so an all-default
    call returns an empty list that matches every approach.

    :return: The strategies to apply, combined conjunctively by the database.
    """
    filters: list[FilterStrategy] = []
    if date is not None:
        filters.append(DateFilter(date))
    if start_date is not None:
        filters.append(StartDateFilter(start_date))
    if end_date is not None:
        filters.append(EndDateFilter(end_date))
    if distance_min is not None:
        filters.append(MinDistanceFilter(distance_min))
    if distance_max is not None:
        filters.append(MaxDistanceFilter(distance_max))
    if velocity_min is not None:
        filters.append(MinVelocityFilter(velocity_min))
    if velocity_max is not None:
        filters.append(MaxVelocityFilter(velocity_max))
    if diameter_min is not None:
        filters.append(MinDiameterFilter(diameter_min))
    if diameter_max is not None:
        filters.append(MaxDiameterFilter(diameter_max))
    if hazardous is not None:
        filters.append(HazardousFilter(hazardous))
    return filters


def _diameter_or_nan(approach: CloseApproach) -> float:
    """Return the NEO's diameter, or NaN when the NEO or diameter is unknown."""
    if approach.neo is None:
        return float("nan")
    return approach.neo.diameter
