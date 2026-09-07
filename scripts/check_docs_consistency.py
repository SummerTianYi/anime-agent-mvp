# -*- coding: utf-8 -*-
"""Documentation-consistency guard: docs must never drift from code again.

The 2026-09-06 rot incident (README/AGENTS/HANDOFF claimed the permission
layer did not exist after it shipped; TESTING.md said 112 tests while 154
existed; .env.example missed every capability variable) happened because
status updates were manual. This script makes the mechanical parts of that
drift impossible to miss: it reconciles documentation claims against code
reality and exits non-zero on any mismatch.

Checks (all offline, no API calls, no side effects):
  1. Test-count claims in current-status docs match the actual number of
     unittest cases discoverable under services/agent-core/tests.
  2. Every environment variable read by agent_core code appears in
     .env.example (system vars excluded).
  3. Every tool registered in agent_core.tools appears in the AVATAR_BRIDGE
     tool documentation.

Run from the repository root with the agent-core venv:
  .\\services\\agent-core\\.venv\\Scripts\\python.exe .\\scripts\\check_docs_consistency.py
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "services" / "agent-core"

# Docs whose test-count claims must match reality. Archival docs
# (CONTRIBUTIONS / EXAM_LEDGER / TEST_REPORT) hold historical numbers on
# purpose and are deliberately not scanned.
STATUS_DOCS = [
    REPO / "docs" / "TESTING.md",
    REPO / "README.md",
    REPO / "AGENTS.md",
    REPO / "docs" / "HANDOFF.md",
    REPO / "docs" / "VERIFICATION_SPEC.md",
    REPO / "docs" / "MVP.md",
]
COUNT_PATTERNS = [
    re.compile(r"(\d+)\s*tests? pass", re.IGNORECASE),
    re.compile(r"(\d+)\s*项单测"),
    re.compile(r"(\d+)\s*项测试"),
    re.compile(r"(\d+)\s*项全绿"),
    re.compile(r"[Cc]urrently\s+(\d+)"),
    re.compile(r"测试总数基线（[^\）]*?(\d+)"),
]
# System-provided variables that code may read but .env.example must not list.
ENV_EXEMPT = {"LOCALAPPDATA", "USERPROFILE", "APPDATA", "SYSTEMROOT", "TEMP", "TMP", "PATH", "HOME"}


def discover_test_count() -> int:
    # Mirrors the proven TESTING.md invocation (cd services\agent-core;
    # python -m unittest discover -s tests): "agent-core" is not a legal
    # package name, so tests are discovered as top-level modules.
    sys.path.insert(0, str(CORE))
    try:
        suite = unittest.TestLoader().discover(str(CORE / "tests"))
    finally:
        sys.path.pop(0)
    return suite.countTestCases()


def claimed_counts() -> list[tuple[Path, int, str]]:
    claims: list[tuple[Path, int, str]] = []
    for doc in STATUS_DOCS:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            for pattern in COUNT_PATTERNS:
                for match in pattern.finditer(line):
                    claims.append((doc, int(match.group(1)), line.strip()[:100]))
    return claims


def code_env_vars() -> set[str]:
    names: set[str] = set()
    for py_file in sorted((CORE / "agent_core").glob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_getenv = (
                (isinstance(func, ast.Name) and func.id in ("getenv", "getenvbool"))
                or (isinstance(func, ast.Attribute) and func.attr in ("getenv", "get"))
            )
            if not is_getenv or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                name = first.value
                if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", name):
                    names.add(name)
    return names


def example_env_vars() -> set[str]:
    text = (REPO / ".env.example").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Z][A-Z0-9_]+)=", text, re.MULTILINE))


def registered_tools() -> set[str]:
    sys.path.insert(0, str(CORE))
    try:
        from agent_core.tools import build_tool_registry

        return set(build_tool_registry().keys())
    finally:
        sys.path.pop(0)


def documented_tools() -> set[str]:
    text = (REPO / "docs" / "AVATAR_BRIDGE.md").read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"`([a-z_]+)`", text))


def main() -> int:
    failures: list[str] = []
    actual = discover_test_count()
    print(f"[1] actual unittest cases: {actual}")
    for doc, number, line in claimed_counts():
        status = "ok" if number == actual else "MISMATCH"
        print(f"    {doc.relative_to(REPO)}: claims {number} ({status})")
        if number != actual:
            failures.append(f"{doc.relative_to(REPO)} claims {number} tests, actual {actual}: {line}")

    code_vars = {v for v in code_env_vars() if v not in ENV_EXEMPT}
    example_vars = example_env_vars()
    missing = sorted(code_vars - example_vars)
    print(f"[2] code env vars: {len(code_vars)}, .env.example entries: {len(example_vars)}")
    if missing:
        failures.append(f".env.example is missing vars read by code: {missing}")
        print(f"    MISSING: {missing}")
    else:
        print("    all code vars documented")

    tools = registered_tools()
    bridge = documented_tools()
    undocumented = sorted(t for t in tools if t not in bridge)
    print(f"[3] registered tools: {sorted(tools)}")
    if undocumented:
        failures.append(f"tools not documented in AVATAR_BRIDGE.md: {undocumented}")
        print(f"    UNDOCUMENTED: {undocumented}")
    else:
        print("    all tools documented in AVATAR_BRIDGE.md")

    if failures:
        print("DOCS_CONSISTENCY_FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("DOCS_CONSISTENCY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
