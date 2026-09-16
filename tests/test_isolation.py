"""run_sql_file must isolate each file's DDL/DML side effects between calls:
comparing two query files is only meaningful if both start from the same state."""
import qq


def test_ddl_does_not_leak_between_files(db, sql_dir):
    a = sql_dir / "a.sql"
    b = sql_dir / "b.sql"
    a.write_text("CREATE TABLE iso (x int); INSERT INTO iso VALUES (7); SELECT x FROM iso;")
    b.write_text("SELECT x FROM iso;")
    r1 = qq.run_sql_file(str(a), db)
    assert r1["results"][0]["rows"] == [(7,)]
    r2 = qq.run_sql_file(str(b), db)
    assert r2["results"] == []
    assert len(r2["errors"]) == 1
    assert "iso" in r2["errors"][0][2]  # relation must NOT exist after rollback


def test_identical_ddl_files_both_run_clean(db, sql_dir):
    a = sql_dir / "a.sql"
    b = sql_dir / "b.sql"
    sql = "CREATE TABLE dup (x int); INSERT INTO dup VALUES (1); SELECT x FROM dup ORDER BY x;"
    a.write_text(sql)
    b.write_text(sql)
    r1 = qq.run_sql_file(str(a), db)
    r2 = qq.run_sql_file(str(b), db)
    assert r1["errors"] == [] and r2["errors"] == []
    for x, y in zip(r1["results"], r2["results"]):
        assert x["columns"] == y["columns"]
        assert x["types"] == y["types"]
        assert x["rows"] == y["rows"]


def test_error_inside_file_does_not_poison_later_statements(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text("CREATE TABLE e_t (x int); SELECT * FROM gone; INSERT INTO e_t VALUES (1); SELECT x FROM e_t;")
    r = qq.run_sql_file(str(f), db)
    assert len(r["errors"]) == 1
    # the INSERT after the failing statement still succeeded (savepoint rollback)
    assert [x["rows"] for x in r["results"]] == [[(1,)]]
