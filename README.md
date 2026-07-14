# NEO Explorer — Near-Earth Object Explorer

A command-line tool (CLI) that reads real NASA/JPL data about **Near-Earth Objects (NEOs)** and their close approaches to Earth, links them in memory, and enables searching, exploration, and exporting.

The system reads two files:
- **`neos.csv`** — the catalog of objects (designation, name, diameter, whether hazardous).
- **`cad.json`** — the close approach records (time, distance, velocity, and the linking `designation`).

---

## Features

- Load and parse CSV + JSON into Python objects.
- Bidirectional linking between each NEO and its approaches.
- Composable search criteria via the **Strategy Pattern**.
- Thin unified CLI façade via the **Facade Pattern**.
- Export results to CSV or JSON.
- **Zero runtime dependencies** (standard Python library only).

---

## Requirements and Running

- Python ≥ 3.10 (no external dependencies).

```bash
# Works out-of-the-box on the sample data with no arguments
python -m neo_explorer query

# With your real data
python -m neo_explorer --neos data/neos.csv --cad data/cad.json query --hazardous

# Or after installation (provides the neo-explorer command)
pip install -e .
neo-explorer inspect --name Halley
```

> The default paths are the samples `data/neos.sample.csv` and `data/cad.sample.json`, so the system works out of the box. Pass `--neos`/`--cad` for your real data.

---

## Commands

### `query` — Search close approaches

```bash
python -m neo_explorer --neos data/neos.sample.csv --cad data/cad.sample.json \
    query --hazardous --max-distance 0.03 --limit 10
```

| Option | Meaning |
|--------|--------|
| `--date YYYY-MM-DD` | Approaches on a specific date |
| `--start-date` / `--end-date` | Time range |
| `--min-distance` / `--max-distance` | Distance bounds (au) |
| `--min-velocity` / `--max-velocity` | Velocity bounds (km/s) |
| `--min-diameter` / `--max-diameter` | Diameter bounds (km) |
| `--hazardous` / `--no-hazardous` | Restrict to (or exclude) hazardous ones |
| `--limit N` | Limit results (0 = no limit) |
| `--outfile out.csv` / `out.json` | Export instead of printing |

| `--min-*` greater than `--max-*` | Rejected with a clear error message (also `--start-date` after `--end-date`) |
| `--limit` negative | Rejected with an error message |

### `inspect` — Inspect a single NEO

```bash
python -m neo_explorer inspect --name Alpha
python -m neo_explorer inspect --designation "2020 AB" --verbose   # also shows the NEO's approaches
```

| Option | Meaning |
|--------|--------|
| `--designation` / `--name` | Identify the NEO (one is required) |
| `--verbose` | Show the list of the NEO's approaches after its description |

---

## Project Structure

```
neo_explorer/
├── data/                 sample data (CSV/JSON)
└── neo_explorer/
    ├── models.py         NearEarthObject / CloseApproach   (domain objects + __str__)
    ├── extract.py        load_neos / load_approaches        (read files and build objects)
    ├── database.py       NEODatabase                        (indexing + linking + streaming queries)
    ├── filters.py        FilterStrategy + strategies        (Strategy Pattern)
    ├── facade.py         NEOExplorerFacade                  (Facade Pattern)
    ├── write.py          write_to_csv / write_to_json       (exporting)
    ├── display.py        print_approaches / print_neo       (terminal printing)
    ├── cli.py            command adapter                     (argparse → facade)
    └── __main__.py       entry point
```

| Module | Responsibility | Type |
|--------|----------------|------|
| `models.py` | Domain data objects and `__str__` only — no I/O, no parsing | Classes |
| `extract.py` | Read CSV/JSON, convert types, ignore extra fields | Standalone functions |
| `database.py` | Store collections, build indexes, link, lazy `query()` | Class |
| `filters.py` | `FilterStrategy` contract + strategies + `create_filters` | Strategy |
| `facade.py` | Thin unified facade coordinating the other layers | Facade |
| `write.py` / `display.py` | Export / printing | Standalone functions |
| `cli.py` | Read args → filters → facade → display/export | Thin adapter |

---

## Architecture

### Layers (one-way, no cycles)

```
        ┌──────────────────────────────────────────────┐
        │  cli.py  (adapter: args → filters → facade)   │  ← entry/display
        └───────────────┬───────────────────────────────┘
                        │ knows only the Facade
        ┌───────────────▼───────────────────────────────┐
        │  facade.py — NEOExplorerFacade  (thin orchestration) │  ← unified interface
        └───┬──────────────┬───────────────┬─────────────┘
            │              │               │
   ┌────────▼──────┐ ┌─────▼───────┐ ┌─────▼──────────┐
   │  extract.py   │ │ database.py │ │   filters.py    │  ← business logic
   └───────┬───────┘ └─────┬───────┘ └─────┬──────────┘
           └───────────────▼───────────────┘
                    ┌──────────────┐
                    │  models.py   │  ← domain (depends on no one)
                    └──────────────┘

   write.py / display.py  ← output (invoked by the CLI, depend only on models)
```

Rule: dependencies point downward only. `models` is pure and knows no layer, and the CLI knows only the Facade.

### Patterns used

**① Strategy Pattern** — `filters.py`
Each filter criterion is a `@dataclass(frozen=True)` strategy that implements the contract `matches(approach) -> bool`. Filters are composed via `all(f.matches(a) for f in filters)` inside `query`, so adding a new criterion = **just a new class** without modifying the query (OCP).

**② Facade Pattern** — `facade.py`
`NEOExplorerFacade` provides a small interface (`from_files`, `get_neo_by_designation`, `get_neo_by_name`, `search`) and delegates work to the internal layers — no parsing/linking/formatting inside it. The small interface and limited responsibility reduce the risk of it becoming a God Object.

> No other patterns intentionally (no Repository/Factory/ORM) — adhering to KISS/YAGNI.

### Design principles

| Principle | Application |
|--------|---------|
| SRP | Each module has a single responsibility |
| OCP | A new filter does not touch the query |
| DIP | The CLI depends on the Facade abstraction; the Facade is injected with a `NEODatabase` |
| SoC | Domain / Extract / Storage / Filter / Presentation / Export are separated |
| DRY | Centralized conversion in extract; `_diameter_or_nan` and normalization in one place |
| KISS / YAGNI | Dictionaries instead of a database; free functions where there is no state; no excessive abstractions |
| Composition over inheritance | Compose filters and the DB instead of inheritance hierarchies |

---

## Data flow (from start to finish)

Example: `query --hazardous --max-distance 0.03`

```
1. cli.main() → argparse produces the args
2. NEOExplorerFacade.from_files(neos, cad)          ← load once
     ├─ extract.load_neos(csv)       → tuple[NearEarthObject]   (concrete)
     ├─ extract.load_approaches(json)→ tuple[CloseApproach]      (concrete, temporary designation, neo=None)
     └─ NEODatabase(neos, approaches):
           ├─ builds designation index (strip, duplicates → ValueError)
           ├─ builds name index (strip+casefold, first-wins)
           └─ link(): for each approach → approach.neo = neo, and neo.approaches.append(approach)
                        (no match → neo remains None: orphan approach remains)
3. create_filters(...) → [MaxDistanceFilter(0.03), HazardousFilter(True)]
4. facade.search(filters, limit=10):
     └─ database.query(filters)  ← generator: yield approach if all(f.matches(approach))
     └─ islice(results, 10)      ← limiting without converting to a list
5. display.print_approaches(results) ← consumes the generator and prints
```

### Data decisions

- **Missing diameter** = `float("nan")` (not `None`), checked with `math.isnan`; diameter filters do not match unknown.
- **Orphan approach** (no matching NEO): `neo=None`, it remains in the database, searches/displays do not crash because of it.
- **Time** in UTC (`datetime`).
- **concrete vs streaming**: loaded data and indexes are **concrete** (tuple/dict); query results and limiting are **streaming** (generator + `islice`).
- **Extra fields** in CSV/JSON are ignored and not attached to objects.
- **Broken data** (missing `pdes` column, missing field, non-numeric value) produces a clear error message with the row/record number instead of a raw crash.

---

## Testing

```bash
pip install -e ".[dev]"
pytest        # tests for every layer: models / extract / database / filters / facade
ruff check .  # style check (PEP 8)
```

The tests cover: attribute distribution, NaN policy, bidirectional linking, orphan approach, normalization, duplicate keys, filter composition, and lazy streaming.
