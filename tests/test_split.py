"""Tests for split_sql_statements — splitting a .sql file into executable statements.

Rules:
- statements separated by ';' at top level
- ';' inside single-quoted strings, dollar-quoted strings ($$..$$ / $tag$..$tag$),
  line comments (-- ..) and block comments (/* .. */) must NOT split
- comments and whitespace-only fragments are dropped
- order is preserved
"""
from qq import split_sql_statements


def test_simple_multiple_statements():
    sql = "SELECT 1; SELECT 2; SELECT 3;"
    assert split_sql_statements(sql) == ["SELECT 1", "SELECT 2", "SELECT 3"]


def test_no_trailing_semicolon():
    assert split_sql_statements("SELECT 1; SELECT 2") == ["SELECT 1", "SELECT 2"]


def test_semicolon_in_string_literal_not_split():
    sql = r"SELECT 'a;b'; SELECT 2;"
    assert split_sql_statements(sql) == [r"SELECT 'a;b'", "SELECT 2"]


def test_escaped_quote_in_string_literal():
    sql = r"SELECT 'it''s a;b'; SELECT 2;"
    assert split_sql_statements(sql) == [r"SELECT 'it''s a;b'", "SELECT 2"]


def test_dollar_quoted_string_not_split():
    sql = "SELECT $$a;b$c$;$$; SELECT 2;"
    assert split_sql_statements(sql) == ["SELECT $$a;b$c$;$$", "SELECT 2"]


def test_line_comment_not_split_and_stripped():
    sql = "SELECT 1; -- a; comment\nSELECT 2;"
    assert split_sql_statements(sql) == ["SELECT 1", "SELECT 2"]


def test_block_comment_not_split():
    sql = "SELECT /* x; y */ 1; SELECT 2;"
    assert split_sql_statements(sql) == ["SELECT /* x; y */ 1", "SELECT 2"]


def test_comment_only_and_empty_fragments_dropped():
    sql = "  \n  -- only a comment\n  ;  ;\nSELECT 1;"
    assert split_sql_statements(sql) == ["SELECT 1"]


def test_create_table_body_with_semicolons_in_defaults():
    sql = (
        "CREATE TABLE t (a text DEFAULT 'x;y', b int); "
        "INSERT INTO t (a) VALUES ('p;q');"
    )
    assert split_sql_statements(sql) == [
        "CREATE TABLE t (a text DEFAULT 'x;y', b int)",
        "INSERT INTO t (a) VALUES ('p;q')",
    ]
