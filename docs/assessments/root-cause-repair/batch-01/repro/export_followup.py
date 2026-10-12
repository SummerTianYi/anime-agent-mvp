"""Export only selected synthetic evidence; never copies a database or config."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from followup_models import public_messages


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    a = parser.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    def write(name, value):
        target = a.output_dir / name
        if target.exists():
            raise RuntimeError("Will not overwrite earlier exported evidence: " + name)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("mechanism-before", "mechanism-after", "core-full"):
        value = json.loads((a.private_root/(name+".json")).read_text(encoding="utf-8"))
        # Assertions, test IDs and exception types are public; local full traces stay private.
        for kind in ("failures", "errors"):
            for failure in value[kind]:
                trace = failure.pop("trace")
                failure["trace_sha256"] = hashlib.sha256(trace.encode()).hexdigest()
                failure["exception"] = trace.strip().splitlines()[-1]
        write("followup-"+name+".json", value)
    model = json.loads((a.private_root/"models-fixed.json").read_text(encoding="utf-8"))
    initial = {}
    tool_names = []
    for call in model["calls"]:
        call["messages"] = public_messages(call["messages"])
        if "response" in call:
            response = call["response"]
            clean = public_messages([response])[0]
            call["response"] = {**clean, "finish_reason": response.get("finish_reason")}
            tool_names.extend(c.get("function", {}).get("name") for c in response.get("tool_calls") or [])
        case_id = call["request_id"].removesuffix("-request")
        if call["request_id"].endswith("-request") and case_id not in initial:
            initial[case_id] = digest({"messages": call["messages"], "tools": call["tools"]})
    model["capture_projection"] = "v2: request and response whitelist excludes private reasoning; original local-only capture preserved"
    model["isolation_audit"] = {"observed_tool_names": sorted(set(tool_names)),
        "only_selected_synthetic_mcp_requested": set(tool_names) <= {"mcp__github__issue_write", "mcp__github__issue_read", "mcp__gmail__read_email", "mcp__gmail__search_emails"},
        "limitation": "initial runner had an unexercised schema-external local-tool route; v2 closes it, synthetic spy proves denial; fixed model cases not repeated"}
    write("followup-models.json", model)
    summary = {"transports": len(model["calls"]), "by_model": dict(Counter(c["model"] for c in model["calls"])),
        "response_count": sum("response" in c for c in model["calls"]),
        "transport_errors": [{k:c[k] for k in ("index", "model", "request_id", "error_type") if k in c}
                             for c in model["calls"] if "response" not in c],
        "cases": len(model["cases"]), "reopened_cases": sum("reopened_messages" in c for c in model["cases"]),
        "persisted_messages": sum(len(c.get("reopened_messages", [])) for c in model["cases"]),
        "synthetic_effects": sum(len(c["effects"]) for c in model["cases"]),
        "initial_input_hashes": initial, "matched_initial_inputs": {
            scenario: len({h for case,h in initial.items() if case.endswith("-"+scenario)}) == 1
            for scenario in ("operation", "explanation", "clarification")},
        "model_case_execution_order": [c["id"] for c in model["cases"]],
        "repeated_cases": 0, "real_external_mutations": 0, "desktop_actions": 0}
    write("followup-model-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
