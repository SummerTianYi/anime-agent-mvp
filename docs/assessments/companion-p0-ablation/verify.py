"""Recompute the design and audit every recorded transport/turn without issuing a request."""
import argparse
import json
from pathlib import Path

from design import (HERE, PARAMS, PINS, audit_design, build, canonical, digest, expected,
                    lossless, read, rows, schedule)
from agent_core.conversation_context import companion_context
from agent_core.harness import CharacterHarness, SESSION_TITLE_GUIDANCE


def adversarial():
    findings = []
    for case in read("adversarial.json"):
        source = [dict(role=r, content=t) for pair in case["history"]
                  for r, t in zip(("user", "assistant"), pair)]
        scene = {"history": source, "current": case["current"]}
        baseline, _ = expected(scene, "A")
        for arm in "BC":
            body, state = expected(scene, arm)
            lossless([*source, {"role": "user", "content": case["current"]}], body["messages"], state)
            if arm == "B":
                assert body["messages"][1:] == baseline["messages"][1:]
                b_proposals = state["proposals"]
        assert state["proposals"] == b_proposals
        statuses = [p["status"] for p in b_proposals]
        findings.append(dict(id=case["id"], expected_act=case["act"], act=state["act"],
                             expected_states=case["status"], states=statuses, proposals=b_proposals,
                             act_cue=state["act_cue"], status_match=case["status"] == statuses,
                             act_match=case["act"] == state["act"], lossless=True))
    # Independent first-turn, multiline-fact and quoted user-data controls, including genuine questions.
    native = CharacterHarness().build_messages
    source = [{"role": "user", "content": "介绍一下这首歌好吗？"}]
    extra = companion_context(["一条合成事实\n第二行仍为数据"])
    for arm in "ABC":
        on, _, _ = build(native, arm, source, source[-1]["content"], extra, True)
        off, _, _ = build(native, arm, source, source[-1]["content"], extra, False)
        assert on[0]["content"].replace(SESSION_TITLE_GUIDANCE, "", 1) == off[0]["content"]
        assert extra in on[0]["content"] and on[-1] == off[-1] == source[-1]
    return findings


def check_run(folder):
    plans = schedule()
    pins = audit_design()
    assert pins == read("request-pins.json")
    scenes = read("scenes.json")
    all_wire = rows(folder / "requests.jsonl") if (folder / "requests.jsonl").exists() else []
    turns = rows(folder / "dialogues.jsonl") if (folder / "dialogues.jsonl").exists() else []
    summary, = rows(folder / "run.jsonl")
    req = [x for x in all_wire if x["phase"] == "request"]
    res = {x["n"]: x for x in all_wire if x["phase"] == "result"}
    assert len(all_wire) == len(req) + len(res) and len(req) <= 24
    assert [x["n"] for x in req] == list(range(1, len(req)+1))
    assert summary["reserved"] == len(req) and summary["missing"] == list(range(len(req)+1, 25))
    assert [t["n"] for t in turns] == list(range(1, len(turns)+1))
    assert len(turns) <= len(req) + 1 and set(res) <= {r["n"] for r in req}
    assert not any(summary[k] for k in ("clients", "tts_enabled", "wake_started", "recording",
                                          "lifespan_started", "effect_tools"))
    ok, disagreements = 0, []
    for row in req:
        n = row["n"]
        item = plans[n-1]
        scene = scenes[item["scene"]]
        assert all(row[k] == v for k, v in item.items()) and row["code"] == summary["code"]
        assert row["pins"] == PINS
        body, state = expected(scene, item["arm"])
        assert row["body"] == body and digest(canonical(body)) == row["body_sha256"] == pins[
            item["scene"] + "-" + item["arm"]]
        assert {k:v for k,v in body.items() if k != "messages"} == PARAMS
        if n not in res or len(turns) < n or res[n].get("error") or turns[n-1]["error"]:
            assert summary["stop"]
            continue
        t, result = turns[n-1], res[n]
        assert t["code"] == summary["code"] and all(t[k] == v for k,v in item.items())
        assert canonical(t["state"]) == canonical(state)
        source = [*scene["history"], {"role": "user", "content": scene["current"]}]
        assert t["model_history"] == source and t["source_history"] == scene["history"]
        assert t["current"] == scene["current"] and t["first"] == (not scene["history"])
        lossless(source, body["messages"], state)
        assert result["http_post"] and result["model"] == PARAMS["model"]
        choice, = result["choices"]
        raw = choice["message"]["content"]
        parsed, = t["parsed"]
        bubble, = t["bubbles"]
        event = bubble["event"]
        assert raw == parsed["input"] and not parsed["parsed"]["parse_failed"]
        assert CharacterHarness.parse_reply(raw).reply == parsed["parsed"]["reply"]
        if parsed["parsed"]["reply"] != event["text"]:
            disagreements.append(n)
        assert event["type"] == "chat.response" and event["channel"] == "companion" and event["foreground"]
        assert event["conversationId"] > 0 and event["request_id"] == event["turnId"] == "target"
        assert bubble["roles"] == ["avatar", "ui"] and not t["violations"] and not t["core_errors"]
        ok += 1
    if not summary["stop"]:
        assert ok == len(req) == len(res) == len(turns) == 24 and not summary["isolation_violations"]
        assert len({r["response_id"] for r in res.values()}) == 24
    return dict(reservations=len(req), post_count=sum(bool(r.get("http_post")) for r in res.values()),
                successful=ok, raw_parsed_bubble_agree=ok-len(disagreements),
                parsed_bubble_differences=disagreements, missing=summary["missing"], stop=summary["stop"])


def blind(folder):
    # Stable content-independent permutation; labels and arm mapping are withheld during first-pass reading.
    ordered = sorted(rows(folder / "dialogues.jsonl"), key=lambda r: digest("p0-reading-v1/" + str(r["n"])))
    for i, row in enumerate(ordered, 1):
        if not row["error"]:
            print(f"{i:02d} {row['scene']} {row['bubbles'][0]['event']['text']}\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("pins", "adversarial", "run", "blind"))
    p.add_argument("folder", type=Path, nargs="?", default=HERE)
    args = p.parse_args()
    if args.mode == "blind":
        blind(args.folder)
        return
    result = {"pins": audit_design, "adversarial": adversarial,
              "run": lambda: check_run(args.folder)}[args.mode]()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
