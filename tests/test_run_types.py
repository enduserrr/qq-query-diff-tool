"""run_sql_file must capture per-column type names from the result set."""
import qq


def test_run_sql_file_reports_column_types(db, sql_dir):
    f = sql_dir / "q.sql"
    f.write_text("SELECT 1::int AS i, 1.5 AS f, 'x' AS s, now() AS ts;")
    r = qq.run_sql_file(str(f), db)
    types = r["results"][0]["types"]
    assert types[0] == "int4"
    assert types[1] == "numeric"
    # plain string literals: PG<=15 reports 'unknown', PG16+ infers 'text'
    assert types[2] in ("text", "unknown")
    assert types[3] == "timestamptz"
