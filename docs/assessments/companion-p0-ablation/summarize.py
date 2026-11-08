"""Read-only aggregation of the frozen wire evidence and the subsequent semantic reading."""
from collections import defaultdict
import json
from statistics import median

from design import HERE, digest, read, rows
from verify import adversarial, check_run


def summarize():
    capture = check_run(HERE)
    judged = read("ratings.json")
    turns = rows(HERE / "dialogues.jsonl")
    wire = {r["n"]: r for r in rows(HERE / "requests.jsonl") if r["phase"] == "result"}
    blind_order = sorted(turns, key=lambda r: digest("p0-reading-v1/" + str(r["n"])))
    by_arm = defaultdict(list)
    assert len(judged) == len(blind_order)
    for i, (score, turn) in enumerate(zip(judged, blind_order), 1):
        assert score["blind"] == i and turn["n"] == score["n"]
        assert score["protected_pass"] in (0, 1) if turn["scene"] in {"space", "return"} else score["protected_pass"] is None
        assert all(1 <= x <= len(judged) and x != i for x in score["template_peers"])
        by_arm[turn["arm"]].append((turn, score, wire[turn["n"]]))

    metrics = {}
    for arm, samples in sorted(by_arm.items()):
        by_scene = {}
        for name in read("scenes.json"):
            ss = sorted([(t, s) for t, s, _ in samples if t["scene"] == name], key=lambda x:x[0]["repeat"])
            by_scene[name] = {"old_goal": [s["old_goal"] for _, s in ss],
                              "intent": [s["intent"] for _, s in ss],
                              "protected": [s["protected_pass"] for _, s in ss]}
        records = [r for _, _, r in samples]
        elapsed = [r["seconds"] for r in records]
        times = [t["projection_ns"] / 1000 for t, _, _ in samples]
        metrics[arm] = dict(scored=len(samples), by_scene=by_scene,
            primary_old_goal=sum(s["old_goal"] for t,s,_ in samples if t["scene"] in {"praise","switch"}),
            intent=sum(s["intent"] for _, s, _ in samples),
            repeat_question=sum(s["repeat_question"] for _, s, _ in samples),
            template_examples=sum(bool(s["template_peers"]) for _, s, _ in samples),
            ungrounded_examples=sum(bool(s["ungrounded"]) for _, s, _ in samples),
            tokens={k:sum(r["usage"][k] for r in records) for k in (
                "prompt_tokens","completion_tokens","total_tokens","prompt_cache_hit_tokens","prompt_cache_miss_tokens")},
            http_total_s=round(sum(elapsed), 6), http_median_s=round(median(elapsed), 6),
            http_range_s=[min(elapsed),max(elapsed)],
            turn_median_s=round(median(t["turn_seconds"] for t, _, _ in samples), 6),
            projection_median_us=round(median(times), 3), projection_range_us=[min(times),max(times)])
    offline = adversarial()
    assert offline == read("adversarial-results.json")
    return dict(capture=capture, arms=metrics, offline=dict(cases=len(offline),
        acceptance_exact=sum(r["status_match"] for r in offline), act_exact=sum(r["act_match"] for r in offline),
        both=sum(r["act_match"] and r["status_match"] for r in offline),
        lossless=sum(r["lossless"] for r in offline)))


if __name__ == "__main__":
    result = summarize()
    if (HERE / "verification.json").exists():
        assert result == read("verification.json")["recomputed"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
