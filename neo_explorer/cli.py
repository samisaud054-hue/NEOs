"""The command-line interface for the NEO close-approach explorer.

This module is a thin adapter: it parses arguments, turns them into filter
strategies, asks the :class:`~neo_explorer.facade.NEOExplorerFacade` to do the
work, and hands results to the display or export layer. It contains no parsing,
linking, or filtering logic of its own.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Iterable

from . import display, write
from .facade import NEOExplorerFacade
from .filters import create_filters
from .models import CloseApproach

_DEFAULT_NEOS = "data/neos.sample.csv"
_DEFAULT_CAD = "data/cad.sample.json"


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the requested command, and return an exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        facade = NEOExplorerFacade.from_files(args.neos, args.cad)
        return args.handler(facade, args)
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser and its subcommands."""
    parser = argparse.ArgumentParser(
        prog="neo-explorer",
        description="Explore close approaches of near-Earth objects.",
    )
    parser.add_argument("--neos", type=Path, default=_DEFAULT_NEOS, help="Path to the NEO CSV file.")
    parser.add_argument("--cad", type=Path, default=_DEFAULT_CAD, help="Path to the close-approach JSON file.")

    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_query_command(subparsers)
    _add_inspect_command(subparsers)
    return parser


def _add_query_command(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``query`` subcommand for searching close approaches."""
    query = subparsers.add_parser("query", help="Search close approaches by criteria.")
    query.add_argument("--date", type=date.fromisoformat, help="Approaches on this date (YYYY-MM-DD).")
    query.add_argument("--start-date", type=date.fromisoformat, help="Approaches on or after this date.")
    query.add_argument("--end-date", type=date.fromisoformat, help="Approaches on or before this date.")
    query.add_argument("--min-distance", type=_non_negative_float, help="Minimum approach distance in au.")
    query.add_argument("--max-distance", type=_non_negative_float, help="Maximum approach distance in au.")
    query.add_argument("--min-velocity", type=_non_negative_float, help="Minimum relative velocity in km/s.")
    query.add_argument("--max-velocity", type=_non_negative_float, help="Maximum relative velocity in km/s.")
    query.add_argument("--min-diameter", type=_non_negative_float, help="Minimum NEO diameter in km.")
    query.add_argument("--max-diameter", type=_non_negative_float, help="Maximum NEO diameter in km.")
    query.add_argument(
        "--hazardous",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Restrict to (or exclude) potentially hazardous NEOs.",
    )
    query.add_argument("--limit", type=_non_negative_int, default=10, help="Maximum results (0 for no limit).")
    query.add_argument("--outfile", type=Path, help="Write results to a .csv or .json file instead of the console.")
    query.set_defaults(handler=_run_query)


def _add_inspect_command(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``inspect`` subcommand for examining a single NEO."""
    inspect = subparsers.add_parser("inspect", help="Inspect a single NEO by designation or name.")
    target = inspect.add_mutually_exclusive_group(required=True)
    target.add_argument("--designation", help="The NEO's primary designation, e.g. '433'.")
    target.add_argument("--name", help="The NEO's IAU name, e.g. 'Eros'.")
    inspect.add_argument("--verbose", action="store_true", help="Also list the NEO's close approaches.")
    inspect.set_defaults(handler=_run_inspect)


def _run_query(facade: NEOExplorerFacade, args: argparse.Namespace) -> int:
    """Handle the ``query`` subcommand."""
    _validate_ranges(args)
    filters = create_filters(
        date=args.date,
        start_date=args.start_date,
        end_date=args.end_date,
        distance_min=args.min_distance,
        distance_max=args.max_distance,
        velocity_min=args.min_velocity,
        velocity_max=args.max_velocity,
        diameter_min=args.min_diameter,
        diameter_max=args.max_diameter,
        hazardous=args.hazardous,
    )
    results = facade.search(filters, limit=args.limit)
    if args.outfile is not None:
        _export(results, args.outfile)
    else:
        display.print_approaches(results)
    return 0


def _run_inspect(facade: NEOExplorerFacade, args: argparse.Namespace) -> int:
    """Handle the ``inspect`` subcommand."""
    if args.designation is not None:
        neo = facade.get_neo_by_designation(args.designation)
    else:
        neo = facade.get_neo_by_name(args.name)
    if neo is None:
        print("No matching NEO found.")
        return 1
    display.print_neo(neo)
    if args.verbose:
        display.print_approaches(neo.approaches)
    return 0


def _export(results: Iterable[CloseApproach], outfile: Path) -> None:
    """Write query results to a file, choosing the writer by suffix."""
    suffix = outfile.suffix.lower()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".csv":
        write.write_to_csv(results, outfile)
    elif suffix == ".json":
        write.write_to_json(results, outfile)
    else:
        raise ValueError("Output file must end in .csv or .json")
    print(f"Wrote results to {outfile}")


def _validate_ranges(args: argparse.Namespace) -> None:
    """Reject queries whose minimum bound exceeds its maximum bound."""
    bounds = (
        ("distance", args.min_distance, args.max_distance),
        ("velocity", args.min_velocity, args.max_velocity),
        ("diameter", args.min_diameter, args.max_diameter),
    )
    for name, low, high in bounds:
        if low is not None and high is not None and low > high:
            raise ValueError(f"--min-{name} cannot exceed --max-{name}")
    if args.start_date is not None and args.end_date is not None and args.start_date > args.end_date:
        raise ValueError("--start-date cannot be after --end-date")


def _non_negative_float(value: str) -> float:
    """Parse a non-negative float argument, rejecting negatives."""
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _non_negative_int(value: str) -> int:
    """Parse a non-negative integer argument, rejecting negatives."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
