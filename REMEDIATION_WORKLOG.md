# Remediation Worklog — ases_v3_1

Executes MASTER_REMEDIATION_PROMPT.md (D:\omniroute-monetizer). One gap per entry,
verify → fix → test → log → commit.

### [2026-08-22 07:15] GAP-AS-1 — sandbox path mismatch blocks golden path — FIXED

- **Repro (pre-fix):** `agent_service/agent_loop.py:442` (reviewer moat) constructed
  `SandboxExecutor(f"/tmp/ases_sandboxes/{execution_id}")` — UNDERSCORE. The real sandbox
  root is `sandbox.py:30 SANDBOX_BASE_DIR = "/tmp/ases-sandboxes"` — HYPHEN — and
  `create_sandbox()` mounts `{SANDBOX_BASE_DIR}/{execution_id}`. The moat therefore always
  pointed at a directory that never exists → `run_tests()` always failed → reviewer always
  rejected (or, combined with AS-2's fail-open skip, produced garbage verdicts).
- **Fix:**
  1. `sandbox.py`: new `sandbox_workspace_path(execution_id)` helper — the single source of
     truth for host workspace paths; `create_sandbox()` now uses it too.
  2. `agent_loop.py`: reviewer moat now calls `sandbox_workspace_path(execution_id)`;
     hardcoded literal deleted.
- **New tests:** `tests/test_sandbox_path_source_of_truth.py` (3 cases): helper matches the
  create_sandbox root; helper honors SANDBOX_BASE_DIR env override (module reload round-trip);
  static guard asserting no underscore literal or re-derived /tmp sandboxes path remains in
  agent_loop.py.
- **Test output (verbatim):**
  ```
  tests/test_sandbox_path_source_of_truth.py: 3 passed in 0.53s
  tests/test_sandbox.py (existing): 9 passed in 0.65s
  ```
- **Commit:** (with this entry)
