"""Tests for run_sql_file — executing a .sql file against a real Postgres DB."""
import qq


def test_run_sql_file_returns_columns_and_rows(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text(
        "CREATE TABLE t (id int, name text);\n"
        "INSERT INTO t VALUES (1, 'a');\n"
        "INSERT INTO t VALUES (2, 'b');\n"
        "SELECT id, name FROM t ORDER BY id;\n"
    )
    r = qq.run_sql_file(str(f), db)
    assert r["errors"] == []
    assert len(r["results"]) == 1
    res = r["results"][0]
    assert res["columns"] == ["id", "name"]
    assert res["rows"] == [(1, "a"), (2, "b")]
    assert res["seconds"] > 0


def test_run_sql_file_multiple_selects_keep_order(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text("SELECT 1 AS a; SELECT 'two' AS b; SELECT 3 AS c;")
    r = qq.run_sql_file(str(f), db)
    assert [x["columns"] for x in r["results"]] == [["a"], ["b"], ["c"]]
    assert [x["rows"] for x in r["results"]] == [[(1,)], [("two",)], [(3,)]]


def test_run_sql_file_keeps_nulls_and_types(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text(
        "SELECT 42 AS i, 1.5 AS f, 'x' AS s, NULL AS n;"
        "SELECT 3.0::int AS casted, now() AS ts;")
    r = qq.run_sql_file(str(f), db)
    assert r["results"][0]["rows"] == [(42, 1.5, "x", None)]
    assert r["results"][1]["rows"][0][0] == 3
    assert r["results"][1]["rows"][0][1] is not None


def test_run_sql_file_comment_only_has_no_results(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text("-- nothing here\n/* also nothing */\n;")
    r = qq.run_sql_file(str(f), db)
    assert r["results"] == []
    assert r["errors"] == []


def test_run_sql_file_captures_error_and_continues(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text("CREATE TABLE ok_t (x int);\nSELECT * FROM missing_table;\nSELECT 1;\n")
    r = qq.run_sql_file(str(f), db)
    assert len(r["errors"]) == 1
    index, stmt, err = r["errors"][0]
    assert index == 1
    assert "missing_table" in stmt
    assert "missing_table" in err.lower() or "does not exist" in err.lower()
    # statements after the failure still ran
    assert [x["rows"] for x in r["results"]] == [[(1,)]]


def test_run_sql_file_reports_total_seconds(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text("SELECT 1;")
    r = qq.run_sql_file(str(f), db)
    assert r["seconds"] > 0
