# qq — query diff tool (quality control)

Run and diff two `.sql` files against a PostgreSQL database to deeply compare their execution and results.

```bash
python3 qq.py a.sql b.sql
```

## Output
A detailed terminal report comparing everything that can differ:

* **Data:** Missing rows, identical cell counts, row order, and specific cell value differences.
* **Structure:** Changed column names, missing columns, and type differences (e.g., `int4` vs `int8`).
* **Metadata:** Execution time per file and specific statement errors.
* **Verdict:** Final **IDENTICAL** or **DIFFERENT** status.

## Safety & Hard Stops
* **Hard Stops:** A pre-execution regex filter instantly aborts the script (Exit Code 4) if hazardous commands (`INSERT`, `DELETE`, `DROP`, `COMMIT`, `BEGIN`, `nextval`, etc.) are detected in the `.sql` files.
* **Rollbacks:** Each file runs in an isolated transaction that is *always rolled back*.
* **Savepoints:** One failing statement won't abort the rest of the file.


> **Note: For ultimate safety, always run this script using a read-only database user.**
```sql
ALTER USER <user_name> SET default_transaction_read_only = 'on';
```

## Setup & Installation
Requires Python 3 and psycopg2:
```bash
pip install psycopg2-binary
```

Configure your connection via a `DBCONN` dictionary in `settings_overrides.py` in the same directory:

```python
DBCONN = {'user': '', 'password': '', 'host': '', 'port': '', 'dbname': ''}
```

## Exit Codes
* `0` — Results identical
* `1` — Results differ (or a statement errored)
* `2` — Usage or file-not-found error
* `3` — Database connection failed
* `4` — Security abort (hazardous command detected)

## Credits
**NoSleepHermes & [Glm5.3 Flash]** - *For one-shotting 70% of the heavy lifting from a single prompt.*