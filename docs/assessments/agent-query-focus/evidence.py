"""Offline integrity checks for the public model comparison and its acceptance evidence."""
import hashlib
import json
from pathlib import Path
from statistics import median
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/"services/agent-core"))
from agent_core.harness import ACTIVE_PROMPT_OVERRIDE, CharacterHarness


def load(name):
    return json.loads((HERE/name).read_text("utf8"))


def main():
    cases={c["id"]:c for c in load("cases.json")}
    prompts={(p["phase"],p["case"]):p for p in load("evidence/prompts.json")}
    pairs=load("evidence/pairs.json")
    assert sorted(r["slot"] for r in pairs)==list(range(1,13))
    keys={(r["phase"],r["case"],r["provider"]) for r in pairs}
    assert keys=={(phase,case,provider) for phase in ("before","after") for case in cases for provider in ("DS","MiniMax")}
    assert all(r["outcome"]=="received" for r in pairs)
    matched={"before":0,"after":0}
    for row in pairs:
        phase, key=row["phase"],row["case"]
        prompt=prompts[phase,key]
        messages=[{"role":"system","content":ACTIVE_PROMPT_OVERRIDE+prompt["system_suffix"]},
                  {"role":"user","content":prompt["user"]}]
        digest=hashlib.sha256(json.dumps(messages,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
        assert digest==row["prompt_sha256"]==prompt["prompt_sha256"]
        assert (cases[key]["question"] in prompt["user"])==(phase=="after")
        for src in cases[key]["sources"]:
            assert src["content"] in prompt["user"]
        parsed=CharacterHarness.parse_reply(row["content"])
        assert not parsed.parse_failed
        event=row["delivery"]
        assert all(k not in event["text"] for k in ("result_ref","source_numbers","public_web_search"))
        assert event["tts"]
        if phase=="after":
            assert all("https://" not in line for line in event["tts"])
        matched[phase]+=int(all(getattr(parsed,k)==event[k] for k in ("emotion","emotion_intensity","gesture")))
        if phase=="after" and key=="release":
            assert event["text"].splitlines()[:2] in (["4.8.3","2026年10月27号"],["4.8.3","2026年10月27日"])
    assert matched=={"before":1,"after":6}
    tests=load("evidence/checks.json")
    assert tests["core"]["final"]==589 and tests["core"]["failures"]==0
    assert tests["main_slice"]["core"]["last"]=="tests 390 skipped 0 failed []"
    for group in (tests["avatar"],tests["main_slice"]["godot"]):
        assert all(g["passed"] for g in group["gates"])
    print("VERIFIED 6 different prompts, 12 paired HTTP outcomes, 12 Core deliveries",matched)
    for provider in ("DS","MiniMax"):
        stats=[]
        for phase in ("before","after"):
            group=[r for r in pairs if r["phase"]==phase and r["provider"]==provider]
            stats.append({"phase":phase,"median_seconds":median(r["elapsed_seconds"] for r in group),
                          "tokens":sum(r["usage"]["total_tokens"] for r in group)})
        print(provider,stats)


if __name__=="__main__":
    main()
