"""
ASES - Data Models
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class TenantConfig(BaseModel):
    tenant_id: str = "default"
    planner_model: str = "gpt-4o-mini"
    coder_model: str = "gpt-4o"
    reviewer_model: str = "gpt-4o-mini"
    score_threshold: float = 7.0
    design_failure_threshold: float = 0.5  # [v2.10] Classifier threshold for is_design_level_failure. Per-tenant tunable.
    max_iterations: int = 5
    token_budget: int = 50000
    cost_limit_usd: float = 1.00   # hard ceiling per job; overridable per-request
    require_clarity: bool = False  # block underspecified jobs
    clarity_threshold: float = 5.0  # 0-10 threshold to trigger questions
    # GAP-AS-2: when the visual gate cannot run (no Playwright/chromium in the
    # sandbox image, no network for npm, LLM/parse failure), it now FAILS
    # CLOSED (approved=False) instead of silently approving. A tenant that
    # genuinely cannot provision visual review may opt out explicitly; the
    # default keeps the gate blocking so broken UI is never shipped green.
    visual_review_optional: bool = False
    allowed_stacks: List[str] = Field(default_factory=lambda: [
        "Node.js", "Python", "React", "Next.js", "FastAPI", "Express",
        # GAP-AS-4: mobile stacks are now real (wired into sandbox maps),
        # so the planner may offer them. iOS builds still require a macOS
        # runner — documented limitation, enforced at deploy time.
        "React Native", "Expo", "Flutter", "Android",
    ])


class ExecutionResult(BaseModel):
    success: bool
    execution_id: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    error: Optional[str] = None
