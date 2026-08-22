"""GAP-AS-4 regression: mobile stacks are wired, not dead code.

mobile_stacks.py defined RN/Expo/Flutter/iOS/Android images and test
commands but was imported nowhere — a capability claim the product could
not honor. Now sandbox.py merges the mobile maps and TenantConfig offers
the stacks to the planner.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent_service'))

from models import TenantConfig  # noqa: E402
from sandbox import (  # noqa: E402
    ALLOWED_COMMANDS,
    STACK_IMAGES,
    STACK_TEST_COMMANDS,
    _get_image,
    get_test_command,
)


def test_mobile_images_resolved_by_sandbox():
    assert _get_image("flutter") == "cirrusci/flutter:3.22"
    assert _get_image("expo") == "node:18-alpine"
    assert _get_image("android") == "android:34"
    assert "dart" in STACK_IMAGES


def test_mobile_test_commands_resolved_and_allowlisted():
    flutter_cmd = get_test_command("flutter")
    assert "flutter test" in flutter_cmd
    assert flutter_cmd in ALLOWED_COMMANDS
    assert get_test_command("expo") in ALLOWED_COMMANDS
    assert get_test_command("android") in ALLOWED_COMMANDS


def test_planner_offers_mobile_stacks():
    cfg = TenantConfig()
    for stack in ("React Native", "Expo", "Flutter", "Android"):
        assert stack in cfg.allowed_stacks, f"{stack} missing from planner stacks"


def test_stack_maps_still_cover_web_stacks():
    # Merging mobile must not have clobbered the web defaults.
    assert _get_image("fastapi") == "python:3.12-slim"
    assert "npm test" in get_test_command("node.js")
    assert _get_image("unknown-stack-xyz") == STACK_IMAGES["default"]
