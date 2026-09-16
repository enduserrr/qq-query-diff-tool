"""Tests for compare_results — the diff engine (pure function, no DB).

Semantics:
- results are lists of {columns, types, rows}; results are compared 1:1 by index.
- cells are compared positionally: result i vs result i, row i vs row i, col i vs col i.
- rows_missing: multiset difference of whole rows, each direction (capped samples).
- row_order_same: True only when rows are identical as an ordered sequence.
- columns: removed (in A not B), added (in B not A), renamed (content-verified
  1:1 rename when row counts match).
- types: per-cell type-name differences (1-based rows).
- When result counts differ or column shapes differ, cell metrics are None.
"""
from qq import compare_results


def _res(cols, rows, types=None):
    return {"columns": cols, "types": types or [None] * len(cols), "rows": rows}


def test_identical_results():
    a = [_res(["id", "name"], [(1, "x"), (2, "y")], ["integer", "text"])]
    b = [_res(["id", "name"], [(1, "x"), (2, "y")], ["integer", "text"])]
    d = compare_results(a, b)
    assert d["identical"] is True
    assert d["cells"]["pct"] == 100.0
    assert d["row_counts"] == (2, 2)
    assert d["rows_missing"]["a"] == 0 and d["rows_missing"]["b"] == 0
    assert d["row_order_same"] is True
    assert d["cell_diffs"] == []
    assert d["type_diffs"] == []
    assert d["columns"]["removed"] == [] and d["columns"]["added"] == []


def test_single_cell_value_difference():
    a = [_res(["id", "name"], [(1, "x")], ["integer", "text"])]
    b = [_res(["id", "name"], [(1, "y")], ["integer", "text"])]
    d = compare_results(a, b)
    assert d["identical"] is False
    assert d["cells"] == {"total": 2, "same": 1, "pct": 50.0}
    assert d["cell_diffs"] == [{"result": 1, "row": 1, "column": "name", "a": "x", "b": "y"}]
    assert d["rows_missing"] == {"a": 1, "b": 1}  # multiset: each side has 1 unique row
    assert d["row_order_same"] is False


def test_reordered_rows_no_missing():
    a = [_res(["id"], [(1,), (2,), (3,)])]
    b = [_res(["id"], [(2,), (1,), (3,)])]
    d = compare_results(a, b)
    assert d["identical"] is False
    assert d["rows_missing"] == {"a": 0, "b": 0}
    assert d["row_order_same"] is False
    # 1 of 3 aligned cells matches (only the last row)
    assert d["cells"]["pct"] == 100 / 3


def test_missing_rows_each_direction():
    a = [_res(["id"], [(1,), (2,), (3,)])]
    b = [_res(["id"], [(1,), (3,), (99,)])]
    d = compare_results(a, b)
    assert d["rows_missing"]["a"] == 1
    assert d["rows_missing"]["b"] == 1
    assert (2,) in d["row_samples"]["a"]
    assert (99,) in d["row_samples"]["b"]


def test_different_row_counts_positional_cell_compare():
    a = [_res(["id"], [(1,), (2,), (3,)])]
    b = [_res(["id"], [(1,), (3,)])]
    d = compare_results(a, b)
    assert d["rows_missing"]["a"] == 1 and d["rows_missing"]["b"] == 0
    # cells compared over the 2 aligned rows
    assert d["cells"] == {"total": 2, "same": 1, "pct": 50.0}


def test_removed_column():
    a = [_res(["id", "extra"], [(1, "x")])]
    b = [_res(["id"], [(1,)])]
    d = compare_results(a, b)
    assert d["identical"] is False
    assert d["cells"] is None
    assert d["columns"]["removed"] == ["extra"]
    assert d["columns"]["added"] == []


def test_renamed_column_detected():
    a = [_res(["id", "name"], [(1, "x")], ["integer", "text"])]
    b = [_res(["id", "label"], [(1, "x")], ["integer", "text"])]
    d = compare_results(a, b)
    assert d["columns"]["renamed"] == [("name", "label")]
    # positional cell compare still works
    assert d["cells"]["pct"] == 100.0


def test_type_difference_reported():
    a = [_res(["v"], [(1,)], ["integer"])]
    b = [_res(["v"], [(1,)], ["bigint"])]
    d = compare_results(a, b)
    assert d["type_diffs"] == [{"result": 1, "column": "v", "a": "integer", "b": "bigint"}]
    assert d["cells"]["pct"] == 100.0  # values equal, types differ


def test_null_vs_value_is_a_difference():
    a = [_res(["id", "v"], [(1, None)])]
    b = [_res(["id", "v"], [(1, "")])]
    d = compare_results(a, b)
    assert d["cell_diffs"] == [{"result": 1, "row": 1, "column": "v", "a": None, "b": ""}]


def test_case_sensitive_cell_equality():
    a = [_res(["v"], [("A",)])]
    b = [_res(["v"], [("a",)])]
    d = compare_results(a, b)
    assert d["identical"] is False
    assert len(d["cell_diffs"]) == 1


def test_different_result_counts_no_cell_metrics():
    a = [_res(["id"], [(1,)])]
    b = [_res(["id"], [(1,)]), _res(["x"], [(2,)])]
    d = compare_results(a, b)
    assert d["identical"] is False
    assert d["n_results"] == (1, 2)
    assert d["cells"] is None
    assert d["rows_missing"] == {"a": None, "b": None}


def test_cell_diffs_capped():
    rows_a = [(i,) for i in range(500)]
    rows_b = [(i + 1,) for i in range(500)]
    a = [_res(["v"], rows_a)]
    b = [_res(["v"], rows_b)]
    d = compare_results(a, b, max_cell_diffs=10)
    assert d["cells"] == {"total": 500, "same": 0, "pct": 0.0}
    assert len(d["cell_diffs"]) == 10
