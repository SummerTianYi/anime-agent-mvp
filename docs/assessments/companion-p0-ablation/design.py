"""Shared, offline reconstruction of inputs. Gold judgements are never read by the live runner."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = ROOT / "services/agent-core"
sys.path.insert(0, str(CORE))
from agent_core.conversation_context import COMPANION_TURN_GUIDANCE, companion_context
from agent_core.harness import ACTIVE_PROMPT_OVERRIDE, ROLE_PROMPT, RUNTIME_CONTRACT, CharacterHarness
from projection import background_messages, project

BASE = "8025c6bacca57461653090e646ac100ce36e7a27"
MAIN_PERSONA = "cf62b484ca8f075d97c2d4c41496480c7c82501c"
PARAMS = {"model": "deepseek-flash", "stream": False, "thinking": {"type": "disabled"}}
URL = "https://api.deepseek.com/chat/completions"
PINS = {"role": "7f57bf41e8f2764fe9bfbf6797c5323d253d7d1f1a73440873c65d067582207e",
        "runtime": "e43c97d067285fe88688c63c53f97789e6aa306f1d11b8983d2f10a271dc7910",
        "effective": "714ae650ce060f0a645f2fa1055878790438a5e93566ceda18a3ecbdc9d9c9f6",
        "guidance": "9b43195d4297fe4e402c7b276b9b1f20bc8f8e3cfc4becbc2e0fe0369f78c28d"}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args]).decode("utf-8").strip()


def check_pins():
    actual = dict(role=digest(ROLE_PROMPT), runtime=digest(RUNTIME_CONTRACT),
                  effective=digest(ACTIVE_PROMPT_OVERRIDE), guidance=digest(COMPANION_TURN_GUIDANCE))
    assert actual == PINS and len(COMPANION_TURN_GUIDANCE) == 203
    assert (HERE.parent / "companion-v1.2/SYSTEM_PROMPT.txt").read_text(
        encoding="utf-8").rstrip("\n") == ACTIVE_PROMPT_OVERRIDE
    for rev in (BASE, MAIN_PERSONA):
        tree = ast.parse(git("show", rev + ":services/agent-core/agent_core/harness.py"))
        literals = {node.targets[0].id: node.value.value for node in tree.body
                    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Constant)}
        assert (literals["ROLE_PROMPT"], literals["RUNTIME_CONTRACT"]) == (ROLE_PROMPT, RUNTIME_CONTRACT)
    return actual


def schedule():
    plan = read("order.json")
    design = Counter((item["scene"], item["arm"], item["repeat"]) for item in plan)
    assert design == Counter((s, a, r) for s in read("scenes.json") for a in "ABC" for r in (1, 2))
    assert len(plan) == 24
    return plan


def build(native, arm, history, current, extra_system, request_session_title):
    if arm == "A":
        return (native(history, current, extra_system=extra_system, request_session_title=request_session_title),
                {"proposals": None, "act": None, "basis": "仅消息角色与原话"}, 0)
    started = time.perf_counter_ns()
    state, note, demote = project(history, arm)
    extra = extra_system + ("\n\n" + note if note else "")
    elapsed = time.perf_counter_ns() - started
    messages = native(history, current, extra_system=extra, request_session_title=request_session_title)
    started = time.perf_counter_ns()
    background_messages(messages, demote)
    return messages, state, elapsed + time.perf_counter_ns() - started


def expected(scene, arm):
    history = [*scene["history"], {"role": "user", "content": scene["current"]}]
    msgs, state, _ = build(CharacterHarness().build_messages, arm, history, scene["current"],
                           companion_context([]), not scene["history"])
    return {**PARAMS, "messages": msgs}, state


def lossless(source, msgs, state):
    assert len(source) + 1 == len(msgs)
    for i, row in enumerate(source, 1):
        wire = msgs[i]
        assert wire["role"] == row["role"]
        if row["role"] == "user":
            assert wire == row
            continue
        pkt = json.loads(wire["content"])
        positions = state.get("background", {}).get(i, [])
        saved = pkt.pop("过往助手提议（背景）", [])
        assert saved == [row["content"][start:end] for start, end in positions]
        rebuilt = pkt["reply"]
        for (start, _), text in zip(positions, saved):
            rebuilt = rebuilt[:start] + text + rebuilt[start:]
        assert rebuilt == row["content"]
        assert {k: v for k, v in pkt.items() if k != "reply"} == {
            "emotion": "neutral", "emotion_intensity": 0.35, "gesture": "none", "memory_candidate": None}


def audit_design():
    check_pins()
    schedule()
    scenes = read("scenes.json")
    previous = rows(HERE.parent / "companion-experience-p0/requests.jsonl")
    results = {}
    for name, scene in scenes.items():
        source = [*scene["history"], {"role": "user", "content": scene["current"]}]
        baseline, _ = expected(scene, "A")
        if name in {"praise", "space"}:
            prior = next(x for x in previous if x["phase"] == "request" and x["turn"] == f"after-{name}-1-1")
            assert baseline == prior["body"]
        for arm in "ABC":
            body, state = expected(scene, arm)
            lossless(source, body["messages"], state)
            assert body["messages"][0]["content"].startswith(ACTIVE_PROMPT_OVERRIDE + "\n\n" + COMPANION_TURN_GUIDANCE)
            if arm == "B":
                assert body["messages"][1:] == baseline["messages"][1:]
            results[f"{name}-{arm}"] = digest(canonical(body))
    return results
