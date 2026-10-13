# -*- coding: utf-8 -*-
"""Documentation-consistency guard: docs must never drift from code again.

The 2026-09-06 rot incident (README/AGENTS/HANDOFF claimed the permission
layer did not exist after it shipped; TESTING.md said 112 tests while 154
existed; .env.example missed every capability variable) happened because
status updates were manual. This script makes the mechanical parts of that
drift impossible to miss: it reconciles documentation claims against code
reality and exits non-zero on any mismatch.

Checks (offline; import-time storage is confined to a disposable child process):
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
import os
import re
import secrets
import subprocess
import sys
import tempfile
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

ISOLATED_CONFIG = "LLM_PROVIDER=mock\nANIME_AGENT_TTS=0\nANIME_AGENT_WAKE_WORD=0\n"


def prepare_isolation(root: Path) -> dict[str, str]:
    """Called only for a newly allocated TemporaryDirectory; never use caller paths."""
    root = root.resolve(strict=True)
    nonce = secrets.token_hex(24)
    (root / "data").mkdir()
    (root / "isolated.env").write_text(ISOLATED_CONFIG, encoding="utf-8")
    (root / "owner").write_text(nonce, encoding="ascii")
    environment = {k: v for k, v in os.environ.items() if not k.startswith(
        ("ANIME_AGENT_", "LLM_", "DEEPSEEK_", "GLM_", "STEPFUN_", "DOCS_CHECK_"))}
    environment.update(DOCS_CHECK_ROOT=str(root), DOCS_CHECK_NONCE=nonce,
        ANIME_AGENT_DATA_DIR=str(root / "data"), ANIME_AGENT_CONFIG_PATH=str(root / "isolated.env"),
        LLM_PROVIDER="mock", ANIME_AGENT_TTS="0", ANIME_AGENT_WAKE_WORD="0",
        ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_ALLOWED_COMMANDS="",
        ANIME_AGENT_VOICE_INPUT_MODE="manual", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    return environment


def verify_isolation() -> Path:
    raw_root, nonce = os.environ.get("DOCS_CHECK_ROOT", ""), os.environ.get("DOCS_CHECK_NONCE", "")
    if not raw_root or not nonce:
        raise RuntimeError("missing dedicated isolation context")
    root = Path(raw_root).resolve(strict=True)
    expected = {"ANIME_AGENT_DATA_DIR": str(root / "data"),
                "ANIME_AGENT_CONFIG_PATH": str(root / "isolated.env"),
                "LLM_PROVIDER": "mock", "ANIME_AGENT_TTS": "0", "ANIME_AGENT_WAKE_WORD": "0",
                "ANIME_AGENT_MCP_SERVERS": "", "ANIME_AGENT_ALLOWED_COMMANDS": "",
                "ANIME_AGENT_VOICE_INPUT_MODE": "manual"}
    # Compare before opening any configuration or database. An inherited bad
    # path must never become the object of a read, even to validate it.
    if any(os.environ.get(k) != v for k, v in expected.items()):
        raise RuntimeError("isolation environment mismatch")
    for name in ("owner", "data", "isolated.env"):
        if (root / name).resolve(strict=True) != root / name:
            raise RuntimeError("isolation path redirected")
    if (root / "owner").read_text(encoding="ascii") != nonce or (root / "isolated.env").read_text(encoding="utf-8") != ISOLATED_CONFIG:
        raise RuntimeError("isolation files mismatch")
    return root


def install_import_guard(root: Path) -> None:
    """Fail closed if a discovered module attempts ambient storage or I/O."""
    def contained(value):
        return Path(os.fsdecode(value)).resolve().is_relative_to(root)

    def audit(event, args):
        if event == "sqlite3.connect":
            if args[0] != ":memory:" and not contained(args[0]):
                raise RuntimeError("documentation import attempted non-isolated database")
        elif event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path, mode, flags = args
            name = Path(os.fsdecode(path)).name
            private_config = (name.startswith(".env") and name != ".env.example") or name.endswith(".env")
            writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if (private_config or writing) and not contained(path):
                raise RuntimeError("documentation import attempted non-isolated file")
        elif event in {"os.mkdir", "os.remove", "os.rmdir"} and not contained(args[0]):
            raise RuntimeError("documentation import attempted non-isolated mutation")
        elif event in {"socket.connect", "subprocess.Popen", "os.system"}:
            raise RuntimeError("documentation import attempted external I/O")
    sys.addaudithook(audit)


def discover_test_count() -> int:
    verify_isolation()
    # Mirrors the proven TESTING.md invocation (cd services\agent-core;
    # python -m unittest discover -s tests): "agent-core" is not a legal
    # package name, so tests are discovered as top-level modules.
    sys.path.insert(0, str(CORE))
    try:
        loader = unittest.TestLoader()
        suite = loader.discover(str(CORE / "tests"))
        if loader.errors:
            raise RuntimeError("test discovery failed; refusing an incomplete count")
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
    verify_isolation()
    sys.path.insert(0, str(CORE))
    try:
        from agent_core.tools import build_tool_registry

        return set(build_tool_registry().keys())
    finally:
        sys.path.pop(0)


def documented_tools() -> set[str]:
    text = (REPO / "docs" / "AVATAR_BRIDGE.md").read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"`([a-z_]+)`", text))


def run_checks() -> int:
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


def main() -> int:
    try:
        if sys.argv[1:] == ["--isolated"]:
            root = verify_isolation()
            if "agent_core.main" in sys.modules:
                raise RuntimeError("Core was imported before isolation verification")
            sys.dont_write_bytecode = True
            install_import_guard(root)
            result = run_checks()
            print("DOCS_ISOLATION_OK")
            return result
        if sys.argv[1:]:
            raise RuntimeError("unsupported documentation-check arguments")
        # A child guarantees imported modules cannot retain SQLite handles
        # while the parent removes its dedicated temporary directory on Windows.
        with tempfile.TemporaryDirectory(prefix="anime-agent-docs-") as temporary:
            environment = prepare_isolation(Path(temporary))
            return subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--isolated"],
                                  env=environment, cwd=REPO, check=False).returncode
    except (OSError, RuntimeError) as exc:
        print("DOCS_ISOLATION_FAIL: " + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
