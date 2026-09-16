"""CLI behavior tests for qq.py (run via subprocess, no DB needed)."""


def run_cli(args, env=None):
    import subprocess, sys, os
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run([sys.executable, "qq.py"] + args,
                          capture_output=True, text=True, env=e, cwd=os.path.dirname(__file__) + "/..")


def test_no_args_prints_usage_and_exits_2():
    r = run_cli([])
    assert r.returncode == 2
    assert "usage" in r.stderr.lower()


def test_one_arg_prints_usage_and_exits_2():
    r = run_cli(["only_one.sql"])
    assert r.returncode == 2
    assert "usage" in r.stderr.lower()


def test_missing_file_exits_2_with_message(tmp_path):
    r = run_cli([str(tmp_path / "nope1.sql"), str(tmp_path / "nope2.sql")])
    assert r.returncode == 2
    assert "nope1.sql" in r.stderr.lower()
