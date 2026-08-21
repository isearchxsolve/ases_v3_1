"""GAP-AS-3 — REAL unmocked end-to-end golden path.

The pre-existing test_integration_e2e.py mocks every external dependency,
which is exactly how the AS-1 path mismatch and the AS-2 fail-open reviewer
shipped green. This gate has ZERO mocks in the execution path:

Tier 1 (always runs): a real generated project on disk is executed through
the real SandboxExecutor subprocess pipeline with real pytest. Proves the
executor returns truthful verdicts — success for passing tests, failure for
failing tests, failure for a missing directory.

Tier 2 (runs when the Docker daemon is up): the real create_sandbox ->
write_file -> run_command -> cleanup_sandbox container path with a real
pytest run inside the container. Skips LOUDLY (not silently) when the daemon
is unreachable, so the skip is visible evidence, never a hidden gap.

Run:  python -m pytest tests/test_e2e_golden_path.py -m e2e -v --no-cov
"""
import asyncio
import os
import subprocess
import sys
import textwrap

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agent_service"))

from sandbox_executor import SandboxExecutor  # noqa: E402

PASSING_MODULE = textwrap.dedent("""
    def add(a, b):
        return a + b
""")

PASSING_TEST = textwrap.dedent("""
    from app import add

    def test_add():
        assert add(2, 3) == 5
""")

FAILING_TEST = textwrap.dedent("""
    from app import add

    def test_add_broken():
        assert add(2, 3) == 999
""")


def _write_project(tmp_path, test_source):
    (tmp_path / "app.py").write_text(PASSING_MODULE, encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "test_app.py").write_text(test_source, encoding="utf-8")
    return tmp_path


@pytest.mark.e2e
def test_golden_path_real_subprocess_passing(tmp_path):
    """Real files, real subprocess, real pytest — no mocks anywhere."""
    project = _write_project(tmp_path, PASSING_TEST)
    success, output = SandboxExecutor(str(project)).run_tests("python -m pytest -q")
    assert success is True, f"golden path must pass:\n{output}"
    assert "1 passed" in output


@pytest.mark.e2e
def test_golden_path_real_subprocess_failing_is_fail_closed(tmp_path):
    project = _write_project(tmp_path, FAILING_TEST)
    success, output = SandboxExecutor(str(project)).run_tests("python -m pytest -q")
    assert success is False, "a failing test suite must never report success"
    assert "1 failed" in output


@pytest.mark.e2e
def test_golden_path_missing_dir_is_fail_closed(tmp_path):
    success, output = SandboxExecutor(str(tmp_path / "nope")).run_tests()
    assert success is False
    assert "does not exist" in output


def _docker_daemon_up() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True,
                           text=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


@pytest.mark.e2e
def test_golden_path_real_container(tmp_path):
    """Real Docker container golden path. Skips LOUDLY when the daemon is
    down — the skip message is the evidence trail, never a silent pass."""
    if not _docker_daemon_up():
        pytest.skip(
            "GAP-AS-3 container tier BLOCKED: Docker daemon unreachable on "
            "this host. Start Docker Desktop and re-run; this skip is "
            "deliberately loud so the gap stays visible.")

    import sandbox as sb

    execution_id = "e2egolden01"
    container = asyncio.run(sb.create_sandbox(execution_id, "python"))
    try:
        project = _write_project(tmp_path, PASSING_TEST)
        for rel in ("app.py", "tests/__init__.py", "tests/test_app.py"):
            sb.write_file(container, rel,
                          (project / rel).read_text(encoding="utf-8"))
        result = asyncio.run(
            sb.run_command(container, "python -m pytest -q", timeout=120))
        assert result["success"] is True, result["stderr"]
        assert "1 passed" in result["stdout"]
    finally:
        asyncio.run(sb.cleanup_sandbox(container))
