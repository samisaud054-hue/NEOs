"""End-to-end tests for the command-line interface."""

import json

import pytest

from neo_explorer.cli import main


@pytest.fixture
def data_paths(tmp_path) -> tuple[str, str]:
    csv_path = tmp_path / "neos.csv"
    csv_path.write_text(
        "pdes,name,diameter,pha\n2020 AB,Alpha,0.4,Y\n2021 CD,,0.1,N\n",
        encoding="utf-8",
    )
    json_path = tmp_path / "cad.json"
    json_path.write_text(
        json.dumps(
            {
                "fields": ["des", "cd", "dist", "v_rel"],
                "data": [
                    ["2020 AB", "2025-Jan-01 12:00", "0.02", "18.0"],
                    ["2021 CD", "2025-Jan-02 09:30", "0.05", "10.0"],
                ],
            }
        ),
        encoding="utf-8",
    )
    return str(csv_path), str(json_path)


def _argv(data_paths: tuple[str, str], *rest: str) -> list[str]:
    neos, cad = data_paths
    return ["--neos", neos, "--cad", cad, *rest]


def test_query_prints_matches(data_paths, capsys):
    assert main(_argv(data_paths, "query", "--hazardous")) == 0
    assert "2020 AB" in capsys.readouterr().out


def test_query_exports_json(data_paths, tmp_path):
    outfile = tmp_path / "results.json"
    assert main(_argv(data_paths, "query", "--outfile", str(outfile))) == 0
    assert len(json.loads(outfile.read_text(encoding="utf-8"))) == 2


def test_inspect_found_and_verbose(data_paths, capsys):
    assert main(_argv(data_paths, "inspect", "--name", "Alpha", "--verbose")) == 0
    out = capsys.readouterr().out
    assert "Alpha" in out
    assert "approaches Earth" in out  # verbose lists the approach line


def test_inspect_not_found_returns_1(data_paths, capsys):
    assert main(_argv(data_paths, "inspect", "--designation", "9999 ZZ")) == 1
    assert "No matching NEO found." in capsys.readouterr().out


def test_min_exceeds_max_is_rejected(data_paths):
    with pytest.raises(SystemExit):
        main(_argv(data_paths, "query", "--min-distance", "1", "--max-distance", "0.1"))


def test_negative_limit_is_rejected(data_paths):
    with pytest.raises(SystemExit):
        main(_argv(data_paths, "query", "--limit", "-3"))


def test_missing_file_reports_clean_error(tmp_path):
    with pytest.raises(SystemExit):
        main(["--neos", str(tmp_path / "nope.csv"), "--cad", str(tmp_path / "nope.json"), "query"])
