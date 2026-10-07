"""Execute only the deployed continuation condition/assignment on synthetic data.

No Core import, service, database, model call or production write. This proves
the selected branch's state statement, not that it caused a particular answer.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = args.production.resolve() / "services/agent-core/agent_core/main.py"
    raw = path.read_bytes()
    tree = ast.parse(raw.decode("utf-8"))
    handler = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                   and n.name == "_handle_chat_locked")
    matches = [n for n in ast.walk(handler) if isinstance(n, ast.If)
               and "re.fullmatch" in ast.unparse(n.test)
               and n.body and isinstance(n.body[0], ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "confirm_note"
                       for t in n.body[0].targets)]
    if len(matches) != 1:
        raise RuntimeError("Continuation branch is not uniquely identified")
    branch = matches[0]
    assignment = branch.body[0]
    if not isinstance(assignment.value, ast.Constant) or not isinstance(assignment.value.value, str):
        raise RuntimeError("Expected a literal confirmation note")
    # Structural selection is strict; execute only the predicate and literal.
    condition = compile(ast.Expression(branch.test), str(path), "eval")
    cases = [
        ("no-pending-continue", [], {"id": "R2-task"}, "继续"),
        ("pending-continue", [{"id": "R2-action"}], {"id": "R2-task"}, "继续"),
        ("no-task-continue", [], None, "继续"),
        ("no-pending-new-instruction", [], {"id": "R2-task"}, "R2请读取合成页面"),
        ("no-pending-go-on", [], {"id": "R2-task"}, "go on"),
    ]
    rows = []
    for label, pending, task, text in cases:
        selected = bool(eval(condition, {"__builtins__": {}, "re": re},
                             {"pending": pending, "task": task, "text": text}))
        note = assignment.value.value if selected else ""
        rows.append({"case": label, "pending": pending, "task": task, "text": text,
                     "selected": selected, "confirm_note": note,
                     "false_pending_statement": selected and not pending})
    assert [r["selected"] for r in rows] == [True, True, False, False, True]
    assert rows[0]["confirm_note"] == rows[1]["confirm_note"]
    result = {
        "schema": "r2-continuation-counterfactual-v1",
        "layer": "isolated actual AST predicate and literal; no live model causal intervention",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_lines": [branch.lineno, assignment.lineno],
        "condition": ast.unparse(branch.test),
        "preceding_branch_boundary": "cases exclude approve/decline/edit; pending continuation reaches this elif",
        "model_api_calls": 0,
        "observations": rows,
    }
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(result, target, ensure_ascii=False, indent=2)
    print(json.dumps({"observations": len(rows), "false_pending_cases": 2, "model_api_calls": 0}))


if __name__ == "__main__":
    main()
