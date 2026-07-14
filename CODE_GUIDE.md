# Code Guide — Explanation of Every Executable File

This file is a reference for the engineer to understand each module in the project: **what it does, its components, how it works, why it was designed that way, and how it connects to others**.

The explanation order follows the data flow: domain → extraction → storage → filtering → facade → output → entry.

```
models → extract → database → filters → facade → (display / write) → cli → __main__
```

Quick table:

| File | Layer | Exports | Depends on |
|------|-------|---------|------------|
| `models.py` | Domain | `NearEarthObject`, `CloseApproach` | — (stdlib only) |
| `extract.py` | Extraction | `load_neos`, `load_approaches` | `models` |
| `database.py` | Storage+Linking | `NEODatabase` | `models`, `filters` |
| `filters.py` | Filtering | `FilterStrategy`, strategies, `create_filters` | `models` |
| `facade.py` | Facade | `NEOExplorerFacade` | `extract`, `database`, `filters`, `models` |
| `display.py` | Output | `print_approaches`, `print_neo` | `models` |
| `write.py` | Output | `write_to_csv`, `write_to_json` | `models` |
| `cli.py` | Entry | `main` | `facade`, `filters`, `display`, `write`, `models` |
| `__main__.py` | Entry | — | `cli` |
| `__init__.py` | Package | public exports | `models`, `database`, `facade` |

---

## 1) `models.py` — Domain objects

What it does: defines the two core entities of the system as pure data holders. It does not read files, print, or parse raw text. Each entity provides `__str__` for a human-readable description.

### `class NearEarthObject`
Near-Earth object.

| Property | Type | Meaning |
|----------|------|---------|
| `designation` | `str` | the primary identifier (unique) |
| `name` | `str \| None` | the official name (may be `None`) |
| `diameter` | `float` | diameter in kilometers, or `float("nan")` if unknown |
| `hazardous` | `bool` | whether it is potentially hazardous |
| `approaches` | `list[CloseApproach]` | the approaches of this object (starts empty, filled by `NEODatabase`) |

- `fullname` (property): composes the designation and the name in a readable form.
- `__str__`: uses `math.isnan(self.diameter)` to express an unknown diameter.

### `class CloseApproach`
A single close approach to Earth at a point in time.

| Property | Type | Meaning |
|----------|------|---------|
| `designation` | `str` | the designation of the approaching object — **remains after linking** and is used for linking |
| `time` | `datetime` | the time of the approach (UTC) |
| `distance` | `float` | distance (astronomical units, au) |
| `velocity` | `float` | relative velocity (km/s) |
| `neo` | `NearEarthObject \| None` | reference to the object — starts as `None`, assigned by `NEODatabase` |

- `date` (property): the date of the approach (without time) — used by the date filter.
- `__str__`: works even if `neo=None` (an orphaned approach) by falling back to `designation`.

Why this way: separating the domain prevents parsing/printing leakage into it (Separation of Concerns). The models are mutable (not frozen) because linking assigns `neo` and fills `approaches`.

---

## 2) `extract.py` — Reading files and constructing objects

What it does: two standalone functions read the two data files, convert raw values to their types, and construct domain objects. They ignore extra columns/fields. Bad data raises a clear `ValueError` with the row/index number.

### `load_neos(path) -> tuple[NearEarthObject, ...]`
- Opens the CSV with `csv.DictReader`.
- Verifies the presence of the `pdes` column (otherwise raises a clear `ValueError`).
- For each row constructs a `NearEarthObject`: `pdes`→designation, `name`, `diameter` (→NaN if empty), `pha` (→bool).
- Catches conversion errors and re-raises them with the row number.
- Returns a `tuple` (concrete, known-size data).

### `load_approaches(path) -> tuple[CloseApproach, ...]`
- Opens JSON with `json.load` → dict containing `fields` and `data`.
- Builds a map `field → index` and checks for required fields `des, cd, dist, v_rel`.
- For each row reads **only these fields** (ignores extras) and constructs a `CloseApproach` (with `neo=None` and a provisional designation).
- Returns a `tuple`.

### Private helper functions
| Function | Role |
|----------|------|
| `_clean_name(v)` | trimmed text or `None` if empty |
| `_to_float_or_nan(v)` | `float`, or `NaN` if missing |
| `_to_bool(v)` | `Y/yes/true/1` → `True`, otherwise `False` |
| `_to_datetime(v)` | tries several date formats (e.g., `2025-Jan-01 12:00`) |

Why standalone functions: the operation is stateless and doesn't belong to an object (Rubric rule).

---

## 3) `database.py` — Indexing, linking, and querying

What it does: `NEODatabase` stores the loaded collections, builds search indices, **links every approach to its object (and vice versa)**, and streams approaches through filters. No SQL — in-memory dicts provide O(1) lookup.

### `class NEODatabase`

Constructor `__init__(neos, approaches)`:
1. stores the collections as `tuple`s (concrete).
2. builds `_by_designation` (dict).
3. builds `_by_name` (dict).
4. calls `link()`.

`link()` — the bidirectional linking (safe to call multiple times):
```
for neo:  neo.approaches.clear()          # prevents duplication on re-link
for approach:
    neo = _by_designation.get(normalize(approach.designation))
    approach.neo = neo                      # link direction CA → NEO
    if neo: neo.approaches.append(approach) # link direction NEO → CA
    # no match → approach.neo stays None (remains orphaned)
```

Searching:
- `get_neo_by_designation(d)` / `get_neo_by_name(n)`: O(1) lookup after normalization; returns `None` for empty or missing input.

Querying:
- `query(filters=()) -> Iterator[CloseApproach]`: a **generator** that iterates approaches and yields those matching `all(f.matches(a) for f in filters)` — **no if/elif**, and no conversion to a list.

### Indexing policies (private static functions)
| Function | Policy |
|----------|--------|
| `_build_designation_index` | duplicate designations → `ValueError` (identifier must be unique) |
| `_build_name_index` | ignores empty names; on duplicates: **first-wins** (`setdefault`) |

### Normalization (module-level functions)
| Function | Operation |
|----------|-----------|
| `_normalize_designation` | `strip()` |
| `_normalize_name` | `strip().casefold()` (case-insensitive lookup) |

Why this way: linking and indexing are data behaviors (belong to the DB, not the models). Normalization in one place (DRY). `query` is lazy (memory efficient).

---

## 4) `filters.py` — Filtering system (Strategy Pattern)

What it does: converts each search criterion into a small explicit strategy that implements a uniform contract, allowing any set of criteria to be composed without branching logic.

### `class FilterStrategy(Protocol)`
Contract: any object with `matches(approach) -> bool` is considered a filter. (Protocol = structural typing, with no forced inheritance.)

### Concrete strategies (all `@dataclass(frozen=True)`)
| Class | Criterion |
|-------|-----------|
| `DateFilter(on)` | date equals |
| `StartDateFilter(start)` / `EndDateFilter(end)` | time window |
| `MinDistanceFilter` / `MaxDistanceFilter` | distance bounds |
| `MinVelocityFilter` / `MaxVelocityFilter` | velocity bounds |
| `MinDiameterFilter` / `MaxDiameterFilter` | diameter bounds (handles NaN) |
| `HazardousFilter(hazardous)` | hazardous state (guards `neo=None`) |

Each class holds a **single** criterion and implements a clear, type-safe `matches`.

### `create_filters(**criteria) -> list[FilterStrategy]`
- accepts user criteria (all optional).
- builds a list of only the required strategies (criterion `None` = no strategy).
- default call with no criteria → empty list which matches everything.

### `_diameter_or_nan(approach) -> float`
A single helper that returns the object's diameter or `NaN` (for `neo=None` or unknown diameter) — **removes the only duplication** between the two diameter filters.

Why Strategy: adding a new criterion = new class only, without touching `query` (Open/Closed Principle). Composition is via `all(...)` (no if/elif or excessive duplication).

---

## 5) `facade.py` — Unified facade (Facade Pattern)

What it does: `NEOExplorerFacade` is the **single access point for the CLI**. It coordinates loading, storage, and filtering, but **delegates** all actual work — no parsing/linking/formatting happens inside it.

### `class NEOExplorerFacade`
| Member | Role |
|--------|------|
| `__init__(database)` | injects `NEODatabase` (explicit dependency, mockable) |
| `from_files(neos_path, approaches_path)` (classmethod) | loads via `extract`, then constructs `NEODatabase` and returns a ready facade |
| `get_neo_by_designation(d)` | delegates to the DB |
| `get_neo_by_name(n)` | delegates to the DB |
| `search(filters=(), limit=None)` | `database.query(filters)` then `islice(results, limit)` if a limit is provided — **remains streaming** |

Why Facade: isolates the CLI from inner layers (Low Coupling). A small surface area and limited responsibilities reduce the risk of becoming a God Object. `search` applies the limit via `islice` without converting to a list.

---

## 6) `display.py` — Terminal printing

What it does: standalone functions convert domain objects to text and print them. Keeps display logic out of the DB and the Facade.

| Function | Role |
|----------|------|
| `print_approaches(approaches)` | prints each approach; if no results it prints a notice. Consumes an **iterable/generator** (streaming) |
| `print_neo(neo)` | prints the object + the count of its known approaches |

Why standalone functions: display is stateless and does not belong to an object.

---

## 7) `write.py` — Exporting to files

What it does: standalone functions serialize approaches to CSV or JSON. No filtering, no printing, no state.

| Function | Role |
|----------|------|
| `write_to_csv(approaches, path)` | writes CSV with fixed columns; unknown diameter → `""` |
| `write_to_json(approaches, path)` | writes a list of JSON objects; unknown diameter → `null` |
| `_serialize(approach, *, nan_diameter)` (private) | builds a flat record; handles `neo=None` (orphan), empty name, and NaN diameter |

Columns: `datetime_utc, distance_au, velocity_km_s, designation, name, diameter_km, potentially_hazardous`.

Why this way: serialization is kept out of the models (Rubric forbids serialization in the domain). The NaN form differs between CSV (`""`) and JSON (`null`) to produce valid outputs.

---

## 8) `cli.py` — Command-line interface

What it does: a thin adapter that reads arguments, converts them to filters, calls the Facade, and directs results to display/export. **No parsing/linking/filtering inside it.**

### Public and private functions
| Function | Role |
|----------|------|
| `main(argv=None)` | builds the parser, loads the Facade, executes the appropriate handler. Catches `FileNotFoundError/ValueError/KeyError/TypeError` and converts them to a user-friendly error message |
| `_build_parser()` | builds `argparse`: `--neos`/`--cad` (defaults are the sample files) + commands `query` and `inspect` |
| `_add_query_command` | registers `query` options (date/distance/velocity/diameter/hazardous/limit/outfile) |
| `_add_inspect_command` | registers `inspect` (`--designation`/`--name` mutually exclusive + `--verbose`) |
| `_run_query(facade, args)` | validates ranges → `create_filters` → `facade.search` → print or export |
| `_run_inspect(facade, args)` | fetches the object; if found prints it (and `--verbose` prints its approaches); otherwise returns 1 |
| `_export(results, outfile)` | chooses `write_to_csv`/`write_to_json` based on the extension |
| `_validate_ranges(args)` | rejects `min > max` (distance/velocity/diameter) and `start_date > end_date` |
| `_non_negative_float` / `_non_negative_int` | argparse types that reject negative values |

Single command flow: `argv → parse_args → from_files → create_filters → facade.search → display/write`.

Why this way: the CLI is only a presentation/entry layer; all business logic lives in lower layers (SoC + Low Coupling).

---

## 9) `__main__.py` — Entry point

What it does: enables `python -m neo_explorer`. One effective line:
```python
from .cli import main
raise SystemExit(main())
```
It calls `main()` and converts its return value to a process exit code.

---

## 10) `__init__.py` — Package interface

What it does: determines what the package exports for direct import, and holds the package docstring.

It exports via `__all__`: `NearEarthObject`, `CloseApproach`, `NEODatabase`, `NEOExplorerFacade`.

Why: a clear public interface for programmatic use (not the CLI), hiding internal details.

---

## Dependency map (who imports what)

```
__main__ ─▶ cli ─▶ facade ─▶ extract ─▶ models
                 │        └─▶ database ─▶ models
                 │        │           └─▶ filters ─▶ models
                 │        └─▶ filters
                 ├─▶ display ─▶ models
                 ├─▶ write ─▶ models
                 └─▶ filters, models
```

- Direction is one-way (no cycles).
- `models` at the bottom does not import any layer.
- `cli` at the top knows `facade` (+ display/export/filters utilities).

## First-reading tip
Start with `models.py` (understand the data), then `extract.py` (how they are built), then `database.py` (how they are linked and queried), then `filters.py` (how they are filtered), then `facade.py` and `cli.py` (how they are used). For live usage instructions, see `README.md`.
