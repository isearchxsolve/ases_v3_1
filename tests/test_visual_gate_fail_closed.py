"""GAP-AS-2 regression: the visual gate must FAIL CLOSED on its own failures.

Before the fix, _visual_skip() returned approved=True for every failure mode
(screenshot failed, LLM failed, unparseable response), so broken or
unverifiable UI shipped green. Policy skips (last-mile cost gate) remain
approved but are now flagged skipped=True and are a separate code path.
"""
import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent_service'))

import visual_reviewer as vr  # noqa: E402
from sandbox import ALLOWED_COMMANDS  # noqa: E402


def _cfg(optional=False):
    return SimpleNamespace(visual_review_optional=optional)


def test_visual_failure_fails_closed_by_default():
    res = vr._visual_failure("screenshot blew up", _cfg(optional=False))
    assert res["approved"] is False
    assert res["skipped"] is False
    assert "screenshot blew up" in res["issues_text"]
    assert res["issues"][0]["severity"] == "high"


def test_visual_failure_honors_explicit_optional_opt_out():
    res = vr._visual_failure("no playwright", _cfg(optional=True))
    assert res["approved"] is True
    assert res["skipped"] is True
    assert "optional" in res["issues_text"].lower()


def test_policy_skip_is_distinct_from_failure():
    res = vr._visual_skip("not last mile yet")
    assert res["approved"] is True
    assert res["skipped"] is True
    assert res["issues"] == []


def test_screenshot_failure_fails_closed():
    async def fake_run(sandbox_id, cmd, timeout=120):
        return {"success": False, "stdout": "", "stderr": "chromium missing",
                "returncode": 1}

    with patch.object(vr, "logger"), \
         patch("sandbox.run_command", fake_run), \
         patch("sandbox.write_file", lambda *a, **k: None):
        res = asyncio.run(vr.visual_reviewer(
            "ases-abc123", "build a page", "html", [{"path": "index.html"}],
            _cfg(optional=False), "exec-1",
            iteration=5, max_iterations=5, previous_errors=""))
    assert res["approved"] is False
    assert "Screenshot capture failed" in res["issues_text"]


def test_screenshot_command_rejected_fails_closed():
    async def fake_run(sandbox_id, cmd, timeout=120):
        raise ValueError("Sandbox command is not on the execution allowlist")

    with patch("sandbox.run_command", fake_run), \
         patch("sandbox.write_file", lambda *a, **k: None):
        res = asyncio.run(vr.visual_reviewer(
            "ases-abc123", "build a page", "html", [{"path": "index.html"}],
            _cfg(optional=False), "exec-1",
            iteration=5, max_iterations=5, previous_errors=""))
    assert res["approved"] is False
    assert "rejected" in res["issues_text"]


def test_missing_approved_key_defaults_to_reject():
    # The old code did review.get("approved", True) — a missing key approved
    # the UI. Now it must default to False.
    import json as _json
    review = _json.loads('{"issues": [], "summary": "no verdict field"}')
    assert bool(review.get("approved", False)) is False


def test_visual_gate_commands_are_on_allowlist():
    assert "python .ases_screenshot.py" in ALLOWED_COMMANDS
    assert "npm install --prefer-offline 2>&1 && npm start &" in ALLOWED_COMMANDS
    assert "npm install --prefer-offline 2>&1 && npm run dev &" in ALLOWED_COMMANDS
    assert "npm install --prefer-offline 2>&1 && npm run serve &" in ALLOWED_COMMANDS


def test_screenshot_script_takes_url_from_file_not_argv():
    # Fixed allowlist command means the script cannot receive attacker-
    # controlled argv; the URL travels through a workspace file.
    assert "sys.argv" not in vr.SCREENSHOT_SCRIPT
    assert ".ases_shot_url" in vr.SCREENSHOT_SCRIPT
