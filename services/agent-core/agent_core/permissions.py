"""Permission gate for the agent tool loop (zcode, phase B 前置 + T1 三档).

Ported from the anime-agent-workbench Task C implementation and adapted to
the main-repo runtime. Deny by default: every tool invocation is evaluated
against an ordered rule list; unmatched requests are rejected with an
attributable rule_id so decisions can be audited and replayed.

Three-tier decisions (T1 写入工具起):
  "allow" — execute immediately
  "ask"   — hold the call; the character asks the user in chat and the call
            only runs after an explicit confirmation
  "deny"  — reject outright

One hard denial sits above the rule list and can never be allow-listed
away: malformed (non-dict) arguments. Path traversal ('..') is also
hard-denied here; absolute paths are legitimate for the read tools (the
allow-list roots check inside tools.py is the real boundary for those).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

READ_ONLY_TOOLS = ("get_time", "read_file", "list_dir", "screenshot", "active_window", "clipboard_read")
WRITE_TOOLS = ("write_file",)
COMMAND_TOOLS = ("run_command",)
MCP_PREFIX = "mcp__"

ALLOW, ASK, DENY = "allow", "ask", "deny"


@dataclass(frozen=True, slots=True)
class ActionRequest:
    tool: str
    arguments: dict
    origin: str  # "user" | "agent" | "schedule"
    session_id: int | None


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    kind: str  # "allow" | "ask" | "deny"
    rule_id: str
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.kind == ALLOW

    @property
    def needs_confirmation(self) -> bool:
        return self.kind == ASK


@dataclass(frozen=True, slots=True)
class PolicyRule:
    rule_id: str
    match_tool: str  # exact name or "*"
    match_origin: str  # exact origin or "*"
    decision: str = DENY  # "allow" | "ask" | "deny"
    note: str = ""
    constraints: tuple = field(default=())


def _path_traversal(value: str) -> bool:
    """True if the string contains path traversal ('..' segments)."""
    v = value.replace("\\", "/")
    return ".." in v.split("/")


_PATH_KEYS = ("path", "file", "target", "filename", "directory", "dir", "root")
_CONTENT_KEYS = ("content", "text", "query", "note", "prompt")


def _iter_strings(arguments: dict, prefix: str = ""):
    """Yield (key_path, value, is_path_key) for every string leaf. Keys that
    carry free text the user asked to write (content/text/query/...) are
    flagged as non-path data: traversal checks still apply to them (a '..'
    inside free text is suspicious but harmless), while write-roots checks
    only ever apply to path-like keys."""
    for key, value in arguments.items():
        key_path = f"{prefix}.{key}" if prefix else str(key)
        leaf = key_path.split(".")[-1]
        is_path_key = leaf in _PATH_KEYS
        if isinstance(value, dict):
            yield from _iter_strings(value, key_path)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    yield from _iter_strings(item, f"{key_path}[{index}]")
                elif isinstance(item, str):
                    yield f"{key_path}[{index}]", item, is_path_key
        elif isinstance(value, str):
            yield key_path, value, is_path_key


def default_rules() -> list[PolicyRule]:
    """Read-only tools pre-allowed; write tools require user confirmation
    ("ask"); anything not covered is default-deny."""
    rules = [
        PolicyRule(
            rule_id=f"allow-readonly:{tool}",
            match_tool=tool,
            match_origin="*",
            decision=ALLOW,
            note="只读工具默认放行",
        )
        for tool in READ_ONLY_TOOLS
    ]
    rules += [
        PolicyRule(
            rule_id=f"ask-write:{tool}",
            match_tool=tool,
            match_origin="*",
            decision=ASK,
            note="写入工具需用户确认",
        )
        for tool in WRITE_TOOLS
    ]
    rules += [
        PolicyRule(
            rule_id=f"ask-command:{tool}",
            match_tool=tool,
            match_origin="*",
            decision=ASK,
            note="命令执行需用户确认",
        )
        for tool in COMMAND_TOOLS
    ]
    rules.append(PolicyRule(
        rule_id="ask-privacy:look_at_screen",
        match_tool="look_at_screen",
        match_origin="*",
        decision=ASK,
        note="屏幕内容出机器，需要用户确认",
    ))
    rules.append(PolicyRule(
        rule_id="ask-mcp",
        match_tool=MCP_PREFIX + "*",
        match_origin="*",
        decision=ASK,
        note="MCP 工具需用户确认",
    ))
    return rules


class PermissionEngine:
    """Evaluates action requests against an ordered rule list.

    First matching rule wins and returns its rule_id. Hard denials above
    the rule list: malformed-request (non-dict arguments) and path
    traversal ('..') in any string argument, including nested containers.
    No matching rule -> deny with rule_id "default-deny".
    """

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self.rules = list(rules) if rules is not None else default_rules()

    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        if not isinstance(request.arguments, dict):
            return PolicyDecision(DENY, "malformed-request", "arguments must be a dict")
        for key_path, value, is_path_key in _iter_strings(request.arguments):
            if _path_traversal(value):
                return PolicyDecision(
                    DENY, "path-safety", f"参数 {key_path} 存在路径穿越（'..'）"
                )
        if request.tool in WRITE_TOOLS:
            # write scope is known here: an outside-roots write is denied
            # outright instead of wasting a user confirmation on it. Only
            # path-like keys are checked against the write roots.
            from .tools import _write_roots
            from pathlib import Path as _P
            roots = _write_roots()
            if not roots:
                return PolicyDecision(DENY, "write-disabled", "写入功能未启用")
            for key_path, value, is_path_key in _iter_strings(request.arguments):
                if not is_path_key:
                    continue
                candidate = _P(os.path.expandvars(os.path.expanduser(str(value or ""))))
                lexical = os.path.normcase(os.path.normpath(str(candidate)))
                resolved = os.path.normcase(str(candidate.resolve()))
                inside = any(
                    lexical.startswith(os.path.normcase(str(r.resolve())) + os.sep)
                    or lexical == os.path.normcase(str(r.resolve()))
                    or resolved.startswith(os.path.normcase(str(r.resolve())) + os.sep)
                    or resolved == os.path.normcase(str(r.resolve()))
                    for r in roots
                )
                if not inside:
                    return PolicyDecision(
                        DENY, "write-roots", f"参数 {key_path} 不在允许写入的目录内"
                    )
        for rule in self.rules:
            if rule.match_tool.endswith("*"):
                tool_ok = request.tool.startswith(rule.match_tool[:-1])
            else:
                tool_ok = rule.match_tool == "*" or rule.match_tool == request.tool
            origin_ok = rule.match_origin == "*" or rule.match_origin == request.origin
            if tool_ok and origin_ok:
                return PolicyDecision(
                    rule.decision,
                    rule.rule_id,
                    rule.note or f"decision: {rule.decision}",
                )
        return PolicyDecision(DENY, "default-deny", "未匹配任何放行规则")
