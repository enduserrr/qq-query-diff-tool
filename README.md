# qq — query differ

Run two `.sql` files against a Postgres database and diff their execution and
results in detail, highlighting every difference.

```
python3 qq.py query1.sql query2.sql
```

Typical use: `query1.sql` = the **new** version of a query, `query2.sql` = the
**old** version (or vice-versa — the first argument is reported as `a`, the
second as `b`).

## Output

A report covering everything that can differ between two query outputs:

- **Cells exactly the same: N of M (P%)** — positional cell comparison across
  every result set.
- **Rows missing: X in a, Y in b** — multiset (order-insensitive, duplicate-
  aware) difference of whole rows, each direction, with up to 5 sample rows per
  side.
- **Row order identical: yes/no** — whether the rows come back in the same
  order.
- **Column differences** — columns present in only one file, plus
  content-verified renames (a column removed in `a` + a column added in `b`
  whose values are identical is reported as `a -> b`, not as two diffs).
- **Column type differences** — per-column Postgres type (via `pg_type`), e.g.
  `int4` vs `int8`.
- **Cell differences** — up to 20 individual differing cells (result, row,
  column, value in `a` vs `b`); `NULL` and `''` are distinct.
- **Statement errors** — any statement that failed in either file, with the
  SQL, so a failing `SELECT` is visible rather than silently absent.
- **Execution time** — wall time for each file.
- **VERDICT: IDENTICAL / DIFFERENT**.

## Exit codes

- `0` — results identical
- `1` — results differ (or any statement errored)
- `2` — usage / file-not-found error
- `3` — could not connect to the database

## Choosing the database

`qq.py` connects using the standard `psql` environment variables, so it targets
**any** Postgres the environment points at — no per-database configuration:

```
PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
```

Unset variables fall back to psycopg2 defaults (e.g. a local Unix-socket
`postgres` DB). The same setup `psql` uses, so if `psql` reaches your target
database, `qq.py` will too. The connection details are echoed in the report
header with the password masked.

Example:

```
PGHOST=db.internal PGPORT=5432 PGUSER=reader PGPASSWORD=… PGDATABASE=prod \
  python3 qq.py new.sql old.sql
```

## How it runs the SQL (safety)

- Each file runs inside **its own transaction, which is always rolled back**.
  The two files therefore see the same starting state, and `qq` **never
  persists** any DDL/DML side effects of the queries.
- Each statement runs under a **savepoint**, so one failing statement doesn't
  abort the rest of the file.
- The statement splitter understands single-quoted strings (with `''`
  escapes), dollar-quoted strings (`$$…$$`, `$tag$…$tag$`), `--` line
  comments, and `/* … */` block comments, so it won't split inside them.

## Installing

`qq.py` only needs Python 3 and `psycopg2`:

```
pip install psycopg2-binary
```

## Tests

The suite spins up an ephemeral Postgres in rootless podman (removed after the
tests) and exercises the tool end-to-end against it. It is verified to pass on
both Postgres 9.6 and 16.

```
pytest tests/ -q
QQ_TEST_PG_IMAGE=docker.io/library/postgres:9.6-alpine pytest tests/ -q
```
