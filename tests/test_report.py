"""Tests for build_report — the human-readable diff report."""
from qq import build_report


def _run1():
    return {"results": [{"columns": ["id", "name"], "types": ["int4", "text"],
                          "rows": [(1, "x"), (2, "y")], "seconds": 0.001}],
            "errors": [], "seconds": 0.002}


def _run2():
    return {"results": [{"columns": ["id", "name"], "types": ["int4", "text"],
                          "rows": [(1, "x"), (2, "CHANGED")], "seconds": 0.003}],
            "errors": [], "seconds": 0.004}


def _diff():
    return {
        "identical": False,
        "n_results": (1, 1),
        "row_counts": (2, 2),
        "cells": {"total": 4, "same": 3, "pct": 75.0},
        "cell_diffs": [{"result": 1, "row": 2, "column": "name",
                         "a": "y", "b": "CHANGED"}],
        "type_diffs": [],
        "row_order_same": False,
        "rows_missing": {"a": 1, "b": 1},
        "row_samples": {"a": [(2, "y")], "b": [(2, "CHANGED")]},
        "columns": {"removed": [], "added": [], "renamed": []},
    }


def test_report_contains_required_cell_line():
    out = build_report("a.sql", "b.sql", "host=127.0.0.1 dbname=d",
                       _run1(), _run2(), _diff())
    assert "Cells exactly the same: 3 of 4 (75.00%)" in out


def test_report_contains_required_rows_missing_line():
    out = build_report("a.sql", "b.sql", "host=127.0.0.1 dbname=d",
                       _run1(), _run2(), _diff())
    assert "Rows missing: 1 in a.sql, 1 in b.sql" in out


def test_report_lists_cell_differences():
    out = build_report("a.sql", "b.sql", "host=127.0.0.1 dbname=d",
                       _run1(), _run2(), _diff())
    assert "name" in out and "y" in out and "CHANGED" in out
    assert "row 2" in out.lower() or "row=2" in out.lower()


def test_report_lists_missing_row_samples():
    out = build_report("a.sql", "b.sql", "host=127.0.0.1 dbname=d",
                       _run1(), _run2(), _diff())
    assert "(2, 'CHANGED')" in out


def test_report_identical_case():
    d = _diff()
    d.update({"identical": True, "cells": {"total": 4, "same": 4, "pct": 100.0},
              "cell_diffs": [], "rows_missing": {"a": 0, "b": 0},
              "row_samples": {"a": [], "b": []}, "row_order_same": True})
    out = build_report("a.sql", "b.sql", "h=d", _run1(), _run1(), d)
    assert "Cells exactly the same: 4 of 4 (100.00%)" in out
    assert "Rows missing: 0 in a.sql, 0 in b.sql" in out
    assert "IDENTICAL" in out


def test_report_shows_errors():
    r1 = _run1()
    r1["errors"] = [(1, "SELECT * FROM nope", 'relation "nope" does not exist')]
    out = build_report("a.sql", "b.sql", "h=d", r1, _run2(), _diff())
    assert "does not exist" in out
    assert "nope" in out


def test_report_shows_type_and_column_differences():
    d = _diff()
    d["type_diffs"] = [{"result": 1, "column": "v", "a": "int4", "b": "int8"}]
    d["columns"] = {"removed": ["old_col"], "added": ["new_col"],
                    "renamed": [("name", "label")]}
    r2 = _run2()
    out = build_report("a.sql", "b.sql", "h=d", _run1(), r2, d)
    assert "int4" in out and "int8" in out
    assert "old_col" in out and "new_col" in out
    assert "name" in out and "label" in out
