"""Test fixtures: ephemeral Postgres in rootless podman (removed after tests)."""
import os
import subprocess
import time
import uuid

import psycopg2
import pytest

CONTAINER = "qq-test-pg"
HOST = "127.0.0.1"
PORT = 5433
USER = "postgres"
PASSWORD = "testpw"
IMAGE = os.environ.get("QQ_TEST_PG_IMAGE", "docker.io/library/postgres:16-alpine")


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


@pytest.fixture(scope="session")
def pg_server():
    _run(["podman", "rm", "-f", CONTAINER])  # clear stale container if any
    r = _run(["podman", "run", "-d", "--name", CONTAINER,
              "-e", f"POSTGRES_PASSWORD={PASSWORD}",
              "-p", f"{HOST}:{PORT}:5432", IMAGE])
    assert r.returncode == 0, f"podman run failed: {r.stderr}"
    deadline = time.time() + 120
    last_err = None
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(host=HOST, port=PORT, user=USER,
                                    password=PASSWORD, dbname="postgres",
                                    connect_timeout=2)
            conn.close()
            break
        except Exception as e:  # keep waiting for initdb to finish
            last_err = e
            time.sleep(1)
    else:
        logs = _run(["podman", "logs", CONTAINER]).stdout
        raise AssertionError(f"postgres did not come up: {last_err}\n{logs}")
    yield {"host": HOST, "port": PORT, "user": USER, "password": PASSWORD}
    _run(["podman", "rm", "-f", CONTAINER])


@pytest.fixture
def db(pg_server):
    """Fresh database per test; yields connection kwargs, drops db after."""
    dbname = "qqtest_" + uuid.uuid4().hex[:8]
    admin = psycopg2.connect(host=pg_server["host"], port=pg_server["port"],
                             user=pg_server["user"], password=pg_server["password"],
                             dbname="postgres")
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f"CREATE DATABASE {dbname}")
    yield dict(pg_server, dbname=dbname)
    with admin.cursor() as cur:
        cur.execute(f"DROP DATABASE {dbname}")
    admin.close()


@pytest.fixture
def sql_dir(tmp_path):
    """Directory where tests write .sql fixture files."""
    return tmp_path


@pytest.fixture
def pg_env(db):
    """Env vars pointing qq.py at the ephemeral test database."""
    env = {"PGHOST": db["host"], "PGPORT": str(db["port"]),
           "PGUSER": db["user"], "PGPASSWORD": db["password"],
           "PGDATABASE": db["dbname"], "PATH": "/usr/bin:/bin:/usr/local/bin"}
    return env
