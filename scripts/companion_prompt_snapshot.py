"""Export/verify prompt evidence without importing Core or loading configuration."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "services/agent-core"
EVIDENCE = ROOT / "docs/assessments/companion-v1.2"
sys.path.insert(0, str(CORE))
from agent_core import harness  # noqa: E402; no Core/database/config import


def protected_contracts() -> dict[str, str]:
    """Everything outside the two authorized persona text regions is frozen."""
    source = (CORE / "agent_core/harness.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in {"ROLE_PROMPT", "RUNTIME_CONTRACT"}
            for t in node.targets
        ):
            node.value = ast.Constant(value="<persona-region-checked-separately>")
    before, expression = harness.RUNTIME_CONTRACT.split("【表达与人物表现】", 1)
    perception = expression[expression.index("感知声明必须有本轮实际来源："):]
    stable_identity = harness.ROLE_PROMPT[harness.ROLE_PROMPT.index("你知道自己是由本地程序驱动"):]
    parts = {"harness_non_prompt_ast": ast.dump(tree, include_attributes=False),
             "runtime_before_expression": before, "perception_and_output": perception,
             "virtual_identity_and_music": stable_identity}
    return {name: hashlib.sha256(value.encode("utf-8")).hexdigest() for name, value in parts.items()}


def snapshots() -> dict[str, str]:
    # Only execute the literal effort constant assignments, never main.py.
    tree = ast.parse((CORE / "agent_core/main.py").read_text(encoding="utf-8"))
    names = {"EFFORT_LEVELS", "EFFORT_PROMPT_NOTES"}
    nodes = [n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign)) and any(
        isinstance(t, ast.Name) and t.id in names
        for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
    namespace = {"Any": object}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<static-effort-notes>", "exec"), namespace)
    sections = {"TOOL_GUIDANCE": harness.TOOL_GUIDANCE,
                "TASK_DECISION_CONTRACT": harness.TASK_DECISION_CONTRACT,
                "SESSION_TITLE_GUIDANCE": harness.SESSION_TITLE_GUIDANCE,
                "EFFORT_PROMPT_NOTES": namespace["EFFORT_PROMPT_NOTES"]}
    return {"SYSTEM_PROMPT.txt": harness.ACTIVE_PROMPT_OVERRIDE + "\n",
            "SYSTEM_APPENDICES.json": json.dumps(sections, ensure_ascii=False, indent=2) + "\n"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--freeze-contracts", action="store_true",
                        help="Maintainer only: capture BEFORE modifying the baseline persona")
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.freeze_contracts:
        target = EVIDENCE / "PROTECTED_CONTRACTS.json"
        if target.exists():
            raise SystemExit("Refusing to replace the frozen baseline contract")
        target.write_text(json.dumps(protected_contracts(), indent=2) + "\n", encoding="utf-8")
    for name, value in snapshots().items():
        target = EVIDENCE / name
        if args.write:
            target.write_text(value, encoding="utf-8", newline="\n")
        elif target.read_text(encoding="utf-8") != value:
            raise SystemExit("Snapshot mismatch: " + name)
    expected = json.loads((EVIDENCE / "PROTECTED_CONTRACTS.json").read_text(encoding="utf-8"))
    if expected != protected_contracts():
        raise SystemExit("Protected baseline contract changed")
    print("COMPANION_PROMPT_SNAPSHOT_OK")


if __name__ == "__main__":
    main()
