"""End-to-end CLI tests: qq.py against the ephemeral Postgres DB."""
import os
import subprocess
import sys


def run_cli(args, env, cwd):
    e = dict(os.environ)
    e.update(env)
    qq_path = os.path.join(os.path.dirname(__file__), "..", "qq.py")
    return subprocess.run([sys.executable, qq_path] + args,
                          capture_output=True, text=True, env=e, cwd=cwd)


def test_e2e_identical_queries_exit_0(db, sql_dir, pg_env, tmp_path):
    a = sql_dir / "a.sql"
    b = sql_dir / "b.sql"
    a.write_text("CREATE TABLE t (id int, v text); INSERT INTO t VALUES (1,'a'),(2,'b'); SELECT * FROM t ORDER BY id;")
    b.write_text("CREATE TABLE t (id int, v text); INSERT INTO t VALUES (1,'a'),(2,'b'); SELECT * FROM t ORDER BY id;")
    r = run_cli([str(a), str(b)], pg_env, tmp_path)
    assert r.returncode == 0, r.stderr
    assert "Cells exactly the same" in r.stdout
    assert "100.00%" in r.stdout
    assert "Rows missing: 0 in" in r.stdout
    assert "IDENTICAL" in r.stdout


def test_e2e_different_value_exits_1(db, sql_dir, pg_env, tmp_path):
    a = sql_dir / "a.sql"
    b = sql_dir / "b.sql"
    a.write_text("SELECT 1 AS n, 'same' AS s;")
    b.write_text("SELECT 1 AS n, 'DIFF' AS s;")
    r = run_cli([str(a), str(b)], pg_env, tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "50.00%" in r.stdout
    assert "DIFF" in r.stdout
    assert "DIFFERENT" in r.stdout


def test_e2e_missing_row_reported(db, sql_dir, pg_env, tmp_path):
    a = sql_dir / "a.sql"
    b = sql_dir / "b.sql"
    a.write_text("SELECT i FROM (VALUES (1),(2),(3)) t(i);")
    b.write_text("SELECT i FROM (VALUES (1),(3),(4)) t(i);")
    r = run_cli([str(a), str(b)], pg_env, tmp_path)
    assert r.returncode == 1
    assert "Rows missing: 1 in" in r.stdout
    assert r.stdout.count("Rows missing") == 1


def test_e2e_error_in_file_reported(db, sql_dir, pg_env, tmp_path):
    a = sql_dir / "a.sql"
    b = sql_dir / "b.sql"
    a.write_text("SELECT * FROM no_such_table; SELECT 1;")
    b.write_text("SELECT 1;")
    r = run_cli([str(a), str(b)], pg_env, tmp_path)
    assert r.returncode == 1
    assert "does not exist" in r.stdout
    assert "no_such_table" in r.stdout
