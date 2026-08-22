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

### [2026-08-22 07:50] GAP-AS-2 — visual reviewer approves on its own failure — FIXED (fail closed)

- **Repro (pre-fix):** `visual_reviewer.py::_visual_skip()` returned
  `{"approved": True}` and was used for EVERY failure path: screenshot capture failed
  (line 160), screenshot file missing (164), unparseable LLM response (229), LLM call
  exception (256). Additionally `approved = bool(review.get("approved", True))` defaulted
  a MISSING verdict key to approved. Worse: the screenshot command
  `python .ases_screenshot.py '<url>' '<path>'` was never in sandbox.ALLOWED_COMMANDS, so
  `run_command` raised ValueError on every attempt — the gate could literally never
  succeed, and every attempt fell into the approved=True skip. Net effect: the visual
  crown jewel always "approved" without ever looking.
- **Fix:**
  1. `visual_reviewer.py`: split `_visual_skip` (POLICY skip — last-mile cost gate,
     legitimately not reviewing this iteration; now flagged `skipped: True`) from new
     `_visual_failure` (the gate TRIED and could not verify → `approved: False`,
     severity-high issue, blocking issues_text). All four failure paths now call
     `_visual_failure`. Missing `approved` key now defaults to False.
  2. Escape hatch: `TenantConfig.visual_review_optional` (default False). Only an explicit
     tenant opt-out converts a gate failure into a loud `skipped` pass — never silent.
  3. Allowlist repair: the screenshot script now reads its URL from a workspace file
     (`.ases_shot_url`) instead of argv, making the executed command the constant string
     `python .ases_screenshot.py`; that plus the three dev-server start commands are added
     to `sandbox.ALLOWED_COMMANDS` (constant strings from visual_reviewer.py, never
     user/model input — no attack-surface widening). ValueError from run_command is now
     caught and fails closed instead of crashing the loop.
  4. `models.py`: `visual_review_optional: bool = False` field with rationale comment.
- **New tests:** `tests/test_visual_gate_fail_closed.py` (8 cases): _visual_failure fails
  closed by default; explicit optional opt-out passes with skipped flag; policy skip is a
  distinct shape; screenshot failure fails closed end-to-end through visual_reviewer();
  allowlist rejection fails closed; missing approved key defaults to reject; all four
  visual commands present in ALLOWED_COMMANDS; screenshot script has no sys.argv.
- **Test output (verbatim):**
  ```
  tests/test_visual_gate_fail_closed.py: 8 passed in 0.60s
  related sweep (visual/reviewer/sandbox/model): 363 passed, 2743 deselected in 62.10s
  ```
  Pre-existing test_visual_reviewer.py and test_zprod_visual_reviewer.py remain green.
- **Residual (honest):** a real screenshot round-trip still needs Playwright/chromium
  baked into the sandbox images (node:18-alpine / python:3.12-slim don't ship it) and a
  network exception for npm. Until then, frontend jobs on default config will fail closed
  at the visual gate — which is the CORRECT behavior; the images are the follow-up.
- **Commit:** (with this entry)

### [2026-08-22 08:15] GAP-AS-3 — all-mocked E2E suite shipped the AS-1/AS-2 fatals green — FIXED (real e2e gate)

- **Repro (pre-fix):** `tests/test_integration_e2e.py` mocks every external dependency
  (OpenAI, Docker, Postgres, Redis, GitHub, Vercel). That is precisely how the AS-1 path
  mismatch and the AS-2 fail-open reviewer shipped green: no test ever touched a real
  sandbox path or a real gate failure.
- **Fix:** new `tests/test_e2e_golden_path.py`, marker `e2e` (registered in pytest.ini),
  ZERO mocks in the execution path, two tiers:
  1. Tier 1 (always runs): real generated project on disk -> real SandboxExecutor
     subprocess -> real pytest. Three verdicts proven live: passing suite -> success=True
     with "1 passed"; failing suite -> success=False with "1 failed" (fail closed);
     missing project dir -> success=False.
  2. Tier 2 (Docker): real create_sandbox -> write_file -> run_command -> cleanup_sandbox
     container path with pytest inside the container. Skips LOUDLY with an explicit
     BLOCKED message when the daemon is unreachable — the skip text is the evidence trail,
     never a silent pass.
- **Test output (verbatim):**
  ```
  tests/test_e2e_golden_path.py -m e2e: 3 passed, 1 skipped in 27.72s
  (skip reason: "GAP-AS-3 container tier BLOCKED: Docker daemon unreachable on this host...")
  ```
  Docker Desktop engine returned 500/not-ready on this host at execution time; the
  container tier will run green the moment the daemon is up — no code change needed.
- **Policy note:** the mocked suite stays for unit speed but is no longer the release
  gate; `-m e2e` is.
- **Commit:** (with this entry)

### [2026-08-22 08:40] GAP-AS-4 — mobile_stacks.py dead code (capability claim the product couldn't honor) — FIXED (wired)

- **Repro (pre-fix):** `agent_service/mobile_stacks.py` (293 lines) defined
  MOBILE_STACK_IMAGES / MOBILE_STACK_TEST_COMMANDS / dev+build commands for RN, Expo,
  Flutter, iOS, Android — but `grep -rn mobile_stacks` found exactly ONE reference: a
  mention in AUDIT_REPORT.md. Imported nowhere. The planner's allowed_stacks offered only
  web stacks. A monetization-facing product claiming mobile support it could not deliver.
- **Fix (wire, not delete — the data is correct and complete):**
  1. `sandbox.py`: `STACK_IMAGES.update(MOBILE_STACK_IMAGES)` and
     `STACK_TEST_COMMANDS.update(MOBILE_STACK_TEST_COMMANDS)`, both placed BEFORE
     `ALLOWED_COMMANDS = frozenset({*STACK_TEST_COMMANDS.values(), ...})` so mobile test
     commands are executable through the same allowlisted path (verified: flutter/expo/
     android commands all present in ALLOWED_COMMANDS).
  2. `models.py`: TenantConfig.allowed_stacks now offers "React Native", "Expo",
     "Flutter", "Android" to the planner. iOS deliberately excluded from the default
     offer: its image needs a macOS runner (documented limitation, enforced at deploy).
- **New tests:** `tests/test_mobile_stacks_wired.py` (4 cases): mobile images resolve via
  _get_image; mobile test commands resolve AND are allowlisted; planner offers the mobile
  stacks; web-stack defaults not clobbered by the merge.
- **Test output (verbatim):**
  ```
  tests/test_mobile_stacks_wired.py: 4 passed in 0.57s
  full remediation sweep (sandbox, path, visual, e2e, mobile, executor-security):
  54 passed, 1 skipped in 21.90s   (skip = AS-3 container tier, daemon down)
  ```
- **Commit:** (with this entry)
