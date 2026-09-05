"""Permission gate for the agent tool loop (zcode, phase B 前置).

Ported from the anime-agent-workbench Task C implementation and adapted to
the main-repo runtime. Deny by default: every tool invocation is evaluated
against an ordered rule list; unmatched requests are rejected with an
attributable rule_id so decisions can be audited and replayed.

Two hard denials sit above the rule list and can never be allow-listed
away: malformed (non-dict) arguments, and any string argument that looks
like an absolute path or path traversal (workbench Task E "path-safety").
"""

from __future__ import annotations

from dataclasses import dataclass, field

READ_ONLY_TOOLS = ("get_time", "read_file", "list_dir", "screenshot", "active_window", "clipboard_read")


@dataclass(frozen=True, slots=True)
class ActionRequest:
    tool: str
    arguments: dict
    origin: str  # "user" | "agent" | "schedule"
    session_id: int | None


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    rule_id: str
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PolicyRule:
    rule_id: str
    match_tool: str  # exact name or "*"
    match_origin: str  # exact origin or "*"
    decision: bool
    note: str = ""
    constraints: tuple = field(default=())


def _path_escape(value: str) -> bool:
    """True if the string looks like an absolute path or a traversal attempt."""
    v = value.replace("\\", "/")
    if v.startswith("/") or v.startswith("~"):
        return True
    if len(v) >= 2 and v[1] == ":":
        return True
    return ".." in v.split("/")


def _iter_strings(arguments: dict):
    for value in arguments.values():
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            yield from _iter_strings(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, str):
                    yield item


def default_rules() -> list[PolicyRule]:
    """Read-only tools are pre-allowed for any origin; everything else is
    default-deny until a phase-B write tool ships with explicit rules."""
    return [
        PolicyRule(
            rule_id="allow-readonly",
            match_tool=tool,
            match_origin="*",
            decision=True,
            note="只读工具默认放行",
        )
        for tool in READ_ONLY_TOOLS
    ]


class PermissionEngine:
    """Evaluates action requests against an ordered rule list.

    First matching rule wins and returns its rule_id. Hard denials above
    the rule list: malformed-request (non-dict arguments) and path-safety
    (absolute or traversing paths in any string argument, including nested
    containers). No matching rule -> deny with rule_id "default-deny".
    """

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self.rules = list(rules) if rules is not None else default_rules()

    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        if not isinstance(request.arguments, dict):
            return PolicyDecision(False, "malformed-request", "arguments must be a dict")
        for value in _iter_strings(request.arguments):
            if _path_escape(value):
                return PolicyDecision(
                    False, "path-safety", "绝对路径或 '..' 穿越：参数超出允许范围"
                )
        for rule in self.rules:
            tool_ok = rule.match_tool == "*" or rule.match_tool == request.tool
            origin_ok = rule.match_origin == "*" or rule.match_origin == request.origin
            if tool_ok and origin_ok:
                return PolicyDecision(
                    rule.decision,
                    rule.rule_id,
                    rule.note or ("allowed" if rule.decision else "denied by rule"),
                )
        return PolicyDecision(False, "default-deny", "未匹配任何放行规则")
