"""GAP-AS-1 regression: sandbox workspace path has ONE source of truth.

The reviewer moat previously hardcoded "/tmp/ases_sandboxes/{execution_id}"
(underscore) while create_sandbox() mounts "{SANDBOX_BASE_DIR}/{execution_id}"
with SANDBOX_BASE_DIR defaulting to "/tmp/ases-sandboxes" (hyphen). The two
never matched, so the moat always pointed at a nonexistent directory.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent_service'))

from sandbox import SANDBOX_BASE_DIR, sandbox_workspace_path  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_workspace_path_matches_create_sandbox_root():
    path = sandbox_workspace_path("exec-123")
    assert path == f"{SANDBOX_BASE_DIR}/exec-123"
    assert "/tmp/ases-sandboxes/exec-123" == path


def test_workspace_path_honors_env_override(monkeypatch, tmp_path):
    import importlib
    monkeypatch.setenv("SANDBOX_BASE_DIR", str(tmp_path))
    import sandbox as sandbox_mod
    importlib.reload(sandbox_mod)
    try:
        assert sandbox_mod.sandbox_workspace_path("e1") == f"{tmp_path}/e1"
    finally:
        monkeypatch.delenv("SANDBOX_BASE_DIR", raising=False)
        importlib.reload(sandbox_mod)


def test_no_hardcoded_sandbox_path_literals_remain():
    """The underscore literal and any re-derived /tmp path must be gone from
    the agent loop; only sandbox.py may define the base dir."""
    agent_loop = (REPO_ROOT / "agent_service" / "agent_loop.py").read_text(encoding="utf-8")
    assert "ases_sandboxes" not in agent_loop, (
        "hardcoded underscore sandbox path reintroduced in agent_loop.py")
    assert not re.search(r'["\']/?tmp/[a-z_-]*sandboxes', agent_loop), (
        "agent_loop.py re-derives a sandbox /tmp path instead of using "
        "sandbox.sandbox_workspace_path()")
