#!/usr/bin/env python3
"""qq.py — run two .sql files against a Postgres database and diff their results.

Usage: python3 qq.py <file1.sql> <file2.sql>
"""
import os
import re
import sys
import time
from collections import Counter

import psycopg2

os.system("")
# COLOR = {
#     "HEADER": "\033[95m",
#     "BLUE": "\033[94m",
#     "GREEN": "\033[92m",
#     "RED": "\033[91m",
#     "ESC": "\033[0m",
# }

# Import database settings
try:
    import settings_overrides
except ImportError:
    print(COLOR[RED], "Error: Could not import settings_overrides.py", file=sys.stderr)
    raise SystemExit(1)

USAGE = "usage: python3 qq.py <file1.sql> <file2.sql>"

_DOLLAR_TAG = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")


def _effectively_empty(stmt):
    """True if a statement contains only whitespace and comments (no SQL)."""
    i, n = 0, len(stmt)
    while i < n:
        c = stmt[i]
        if c.isspace():
            i += 1
        elif c == "-" and stmt.startswith("--", i):
            e = stmt.find("\n", i)
            i = n if e == -1 else e + 1
        elif c == "/" and stmt.startswith("/*", i):
            e = stmt.find("*/", i + 2)
            i = n if e == -1 else e + 2
        elif c == "'":
            i += 1
            while i < n:
                if stmt[i] == "'":
                    if i + 1 < n and stmt[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
        elif c == "$" and _DOLLAR_TAG.match(stmt, i):
            tag = _DOLLAR_TAG.match(stmt, i).group(0)
            e = stmt.find(tag, i + len(tag))
            i = n if e == -1 else e + len(tag)
        else:
            return False
    return True


def split_sql_statements(sql):
    """Split a SQL script into statements, honoring string literals, dollar-quoted
    strings, and comments. Returns statements in order, whitespace-stripped,
    dropping empty / comment-only fragments."""
    statements = []
    current = []
    i, n = 0, len(sql)

    def flush():
        stmt = "".join(current).strip()
        if stmt and not _effectively_empty(stmt):
            statements.append(stmt)
        current.clear()

    while i < n:
        ch = sql[i]
        if ch == "'":  # single-quoted string ('' = escaped quote)
            current.append(ch)
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        current.append("''")
                        i += 2
                        continue
                    current.append("'")
                    i += 1
                    break
                current.append(sql[i])
                i += 1
        elif ch == "$" and _DOLLAR_TAG.match(sql, i):  # dollar-quoted string
            tag = _DOLLAR_TAG.match(sql, i).group(0)
            end = sql.find(tag, i + len(tag))
            if end == -1:  # unterminated: keep rest as-is
                current.append(sql[i:])
                i = n
            else:
                current.append(sql[i:end + len(tag)])
                i = end + len(tag)
        elif ch == "-" and sql.startswith("--", i):  # line comment: drop
            end = sql.find("\n", i)
            if end == -1:
                i = n
            else:
                current.append(" ")
                i = end + 1
        elif ch == "/" and sql.startswith("/*", i):  # block comment: keep (non-nested)
            end = sql.find("*/", i + 2)
            if end == -1:
                current.append(sql[i:])
                i = n
            else:
                current.append(sql[i:end + 2])
                i = end + 2
        elif ch == ";":
            flush()
            i += 1
        else:
            current.append(ch)
            i += 1
    flush()
    return statements


def _multiset_missing(a_rows, b_rows):
    """Rows in a not matched by b (and vice versa), as counts."""
    ca, cb = Counter(a_rows), Counter(b_rows)
    return sum((ca - cb).values()), sum((cb - ca).values())


def _renames(ca, cb):
    """1:1 rename candidates: columns in A-not-B and B-not-A with matching content."""
    removed = [c for c in ca if c not in cb]
    added = [c for c in cb if c not in ca]
    return removed, added


def compare_results(results_a, results_b, max_cell_diffs=20):
    """Diff two result sets (lists of {columns, types, rows}) positionally."""
    d = {
        "identical": False,
        "n_results": (len(results_a), len(results_b)),
        "row_counts": (len(results_a[0]["rows"]) if results_a else 0,
                       len(results_b[0]["rows"]) if results_b else 0),
        "cells": None,
        "cell_diffs": [],
        "type_diffs": [],
        "row_order_same": True,
        "rows_missing": {"a": None, "b": None},
        "row_samples": {"a": [], "b": []},
        "columns": {"removed": [], "added": [], "renamed": []},
    }
    if len(results_a) != len(results_b):
        return d
    if any(len(r["columns"]) != len(s["columns"]) for r, s in zip(results_a, results_b)):
        # different column count: structural report only, no cell metrics
        for r, s in zip(results_a, results_b):
            d["columns"]["removed"].extend(c for c in r["columns"] if c not in s["columns"])
            d["columns"]["added"].extend(c for c in s["columns"] if c not in r["columns"])
        return d

    # same column count. Names may differ (renames) — cell compare is still
    # positional by index.
    for r, s in zip(results_a, results_b):
        removed, added = _renames(r["columns"], s["columns"])
        if removed or added:
            d["columns"]["removed"].extend(removed)
            d["columns"]["added"].extend(added)
            if len(r["rows"]) == len(s["rows"]) and removed and added:
                for ra in removed[:]:
                    ia = r["columns"].index(ra)
                    for rb in added[:]:
                        ib = s["columns"].index(rb)
                        if all(a[ia] == b[ib] for a, b in zip(r["rows"], s["rows"])):
                            d["columns"]["renamed"].append((ra, rb))
                            d["columns"]["removed"].remove(ra)
                            d["columns"]["added"].remove(rb)

    total = same = 0
    for n, (r, s) in enumerate(zip(results_a, results_b), start=1):
        cols = r["columns"]
        aligned = min(len(r["rows"]), len(s["rows"]))
        for i in range(aligned):
            for j, col in enumerate(cols):
                va, vb = r["rows"][i][j], s["rows"][i][j]
                total += 1
                if va == vb:
                    same += 1
                elif len(d["cell_diffs"]) < max_cell_diffs:
                    d["cell_diffs"].append(
                        {"result": n, "row": i + 1, "column": col, "a": va, "b": vb})
        for j, col in enumerate(cols):
            if r["types"][j] != s["types"][j]:
                d["type_diffs"].append(
                    {"result": n, "column": col,
                     "a": r["types"][j], "b": s["types"][j]})
        if d["rows_missing"]["a"] is None:
            d["rows_missing"]["a"] = 0
            d["rows_missing"]["b"] = 0
        ma, mb = _multiset_missing(r["rows"], s["rows"])
        d["rows_missing"]["a"] += ma
        d["rows_missing"]["b"] += mb
        if ma:
            for row in (Counter(r["rows"]) - Counter(s["rows"])).elements():
                if len(d["row_samples"]["a"]) < 5:
                    d["row_samples"]["a"].append(row)
        if mb:
            for row in (Counter(s["rows"]) - Counter(r["rows"])).elements():
                if len(d["row_samples"]["b"]) < 5:
                    d["row_samples"]["b"].append(row)
        if r["rows"] != s["rows"]:
            d["row_order_same"] = False
    pct = 100.0 * same / total if total else 100.0
    d["cells"] = {"total": total, "same": same, "pct": pct}
    d["identical"] = (pct == 100.0 and d["rows_missing"] == {"a": 0, "b": 0}
                      and d["row_order_same"] and not d["type_diffs"]
                      and not d["columns"]["removed"] and not d["columns"]["added"]
                      and not d["columns"]["renamed"])
    return d


def _type_names(conn, oids):
    """Resolve Postgres type OIDs to type names via pg_type."""
    oids = list(set(oids))
    if not oids:
        return {}
    cur = conn.cursor()
    try:
        cur.execute("SELECT oid, typname FROM pg_type WHERE oid = ANY(%s)", (oids,))
        return dict(cur.fetchall())
    finally:
        cur.close()


def run_sql_file(path, db_kwargs):
    """Execute a .sql file; return {results:[{columns, types, rows, seconds}],
    errors:[(idx, stmt, msg)], seconds}.

    Each file runs inside its own transaction, which is always rolled back:
    statements are compared from an identical starting state and qq never
    persists the queries' side effects. Each statement runs under a savepoint,
    so one failing statement doesn't poison the rest."""
    with open(path) as fh:
        sql = fh.read()
    conn = psycopg2.connect(**db_kwargs)
    try:
        results, errors = [], []
        all_oids = []
        t_total = time.perf_counter()
        for idx, stmt in enumerate(split_sql_statements(sql)):
            t0 = time.perf_counter()
            cur = conn.cursor()
            try:
                cur.execute("SAVEPOINT qq_sp")
                cur.execute(stmt)
                if cur.description is not None:
                    oids = tuple(d[1] for d in cur.description)
                    all_oids.extend(oids)
                    results.append({
                        "columns": [d[0] for d in cur.description],
                        "_oids": oids,
                        "rows": [tuple(r) for r in cur.fetchall()],
                        "seconds": time.perf_counter() - t0,
                    })
                cur.execute("RELEASE SAVEPOINT qq_sp")
            except psycopg2.Error as e:
                cur.execute("ROLLBACK TO SAVEPOINT qq_sp")
                errors.append((idx, stmt, str(e).strip()))
            finally:
                cur.close()
        names = _type_names(conn, all_oids)
        for r in results:
            r["types"] = [names.get(o, str(o)) for o in r.pop("_oids")]
        conn.rollback()
        return {"results": results, "errors": errors,
                "seconds": time.perf_counter() - t_total}
    finally:
        conn.close()


def _fmt_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, str):
        return repr(v)
    return str(v)


def _fmt_row(row):
    return "(" + ", ".join(_fmt_val(v) for v in row) + ")"


def build_report(name_a, name_b, db_desc, run_a, run_b, diff):
    """Render the full diff report as a string with exact ANSI targeting."""
    
    # ANSI Color Codes
    RESET = "\033[0m"
    A_COLOR = "\033[94m"          # Bright Blue
    B_COLOR = "\033[93m"          # Bright Yellow
    GREY = "\033[90m"             # Bright Black (Grey)
    GREY_CURSIVE = "\033[3;90m"   # Italic + Grey
    WHITE = "\033[97m"            # Bright White
    BG_WHITE_FG_BLACK = "\033[30;47m" # Black text, White background
    BOLD_WHITE = "\033[1;37m"     # Bold White text
    VERDICT_FMT = "\033[1;37;44m" # Bold White text on Dark Blue background

    def fmt_hdr(text): return f"{BOLD_WHITE}{text}{RESET}"
    def fmt_sum(text): return f"{BG_WHITE_FG_BLACK}{text}{RESET}"

    # Helper strings to inject white filenames and return to the current grey state
    wa_top = f"{WHITE}{name_a}{GREY_CURSIVE}"
    wb_top = f"{WHITE}{name_b}{GREY_CURSIVE}"
    wa = f"{WHITE}{name_a}{GREY}"
    wb = f"{WHITE}{name_b}{GREY}"

    L = []
    
    # --- Top Block: Cursive Grey with White Filenames ---
    L.append(f"{GREY_CURSIVE}qq: {wa_top}  vs  {wb_top}{RESET}")
    L.append(f"{GREY_CURSIVE}{db_desc}{RESET}")
    L.append(f"{GREY_CURSIVE}results: {diff['n_results'][0]} in {wa_top}, {diff['n_results'][1]} in {wb_top}{RESET}")
    if diff["row_counts"][0] is not None and diff["n_results"][0] == diff["n_results"][1] == 1:
        L.append(f"{GREY_CURSIVE}rows: {diff['row_counts'][0]} in {wa_top}, {diff['row_counts'][1]} in {wb_top}{RESET}")
    L.append("")

    # --- Summary Block: White Background, Black Text ---
    cells = diff["cells"]
    if cells is None:
        L.append(fmt_sum("Cells exactly the same: n/a (structure mismatch — see below)"))
    else:
        L.append(fmt_sum(f"Cells exactly the same: {cells['same']} of {cells['total']} ({cells['pct']:.2f}%)"))
    
    rm = diff["rows_missing"]
    if rm["a"] is None:
        L.append(fmt_sum("Rows missing: n/a (different number of results)"))
    else:
        L.append(fmt_sum(f"Rows missing: {rm['a']} in {name_a}, {rm['b']} in {name_b}"))
        
    L.append(fmt_sum(f"Row order identical: {'yes' if diff['row_order_same'] else 'no'}"))
    L.append(fmt_sum(f"Execution time: {run_a['seconds']:.3f}s in {name_a}, {run_b['seconds']:.3f}s in {name_b}"))
    L.append("")
    # ---------------------------------------------------

    if run_a["errors"] or run_b["errors"]:
        L.append(fmt_hdr("Statement errors:"))
        for tag, run, fmtr_col, fname in ((name_a, run_a, A_COLOR, wa), (name_b, run_b, B_COLOR, wb)):
            for idx, stmt, msg in run["errors"]:
                L.append(f"{GREY}  [{fname}] statement {idx + 1}: {fmtr_col}{msg}{RESET}")
                L.append(f"{GREY}      SQL: {stmt[:120]}{RESET}")
        L.append("")

    cols = diff["columns"]
    if cols["removed"] or cols["added"] or cols["renamed"]:
        L.append(fmt_hdr("Column differences:"))
        if cols["removed"]:
            L.append(f"{GREY}  only in {wa}: {A_COLOR}{', '.join(cols['removed'])}{RESET}")
        if cols["added"]:
            L.append(f"{GREY}  only in {wb}: {B_COLOR}{', '.join(cols['added'])}{RESET}")
        if cols["renamed"]:
            L.append(f"{GREY}  renamed (content-verified): "
                     + ", ".join(f"{a} -> {b}" for a, b in cols["renamed"]) + f"{RESET}")
        L.append("")

    if diff["type_diffs"]:
        L.append(fmt_hdr("Column type differences:"))
        for t in diff["type_diffs"][:50]:
            L.append(f"{GREY}  result {t['result']}, column {t['column']}: "
                     f"{A_COLOR}{t['a']}{GREY} in {wa} vs {B_COLOR}{t['b']}{GREY} in {wb}{RESET}")
        L.append("")

    if diff["row_samples"]["a"] or diff["row_samples"]["b"]:
        L.append(fmt_hdr("Missing row samples (up to 5 per side):"))
        for row in diff["row_samples"]["a"]:
            L.append(f"{GREY}  only in {wa}: {A_COLOR}{_fmt_row(row)}{RESET}")
        for row in diff["row_samples"]["b"]:
            L.append(f"{GREY}  only in {wb}: {B_COLOR}{_fmt_row(row)}{RESET}")
        L.append("")

    if diff["cell_diffs"]:
        L.append(fmt_hdr(f"Cell differences (first {len(diff['cell_diffs'])}):"))
        for c in diff["cell_diffs"]:
            L.append(f"{GREY}  result {c['result']}, row {c['row']}, column {c['column']}: "
                     f"{A_COLOR}{_fmt_val(c['a'])}{GREY} in {wa} vs {B_COLOR}{_fmt_val(c['b'])}{GREY} in {wb}{RESET}")
        L.append("")

    # --- Final Verdict: Dark Blue Background, Bold White Text ---
    verdict_text = "IDENTICAL — no differences found" if diff["identical"] else "DIFFERENT — see above"
    L.append(f"{VERDICT_FMT}VERDICT: {verdict_text}{RESET}")
    
    return "\n".join(L)


def main(argv):
    if len(argv) != 3:
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)
    for path in argv[1:]:
        if not os.path.isfile(path):
            print(f"qq: file not found: {path}", file=sys.stderr)
            raise SystemExit(2)
    name_a, name_b = argv[1], argv[2]
    
    # Use DBCONN from settings_overrides
    raw_dbconn = settings_overrides.DBCONN
    db_kwargs = dict(raw_dbconn)
    
    # Map 'database' to 'dbname' for psycopg2 compatibility
    if "database" in db_kwargs:
        db_kwargs["dbname"] = db_kwargs.pop("database")
        
    desc = dict(db_kwargs)
    if "password" in desc:
        desc["password"] = "***"
    db_desc = ", ".join(f"{k}={v}" for k, v in desc.items())
    
    try:
        run_a = run_sql_file(name_a, db_kwargs)
        run_b = run_sql_file(name_b, db_kwargs)
    except psycopg2.Error as e:
        print(f"qq: database error: {str(e).strip()}", file=sys.stderr)
        raise SystemExit(3)
    
    diff = compare_results(run_a["results"], run_b["results"])
    if run_a["errors"] or run_b["errors"]:
        diff["identical"] = False
    print(build_report(name_a, name_b, db_desc, run_a, run_b, diff))
    raise SystemExit(0 if diff["identical"] else 1)


if __name__ == "__main__":
    main(sys.argv)
