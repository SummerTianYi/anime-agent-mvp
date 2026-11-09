"""Replay paired model outputs through isolated Core WebSocket, Godot Label and speech input."""
import argparse
import asyncio
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"agent-query-delivery"))
import exercise
from capture import TrialDate


def lines(path):
    return [json.loads(s) for s in path.read_text("utf8").splitlines() if s.strip()]


def main(out, godot):
    out.mkdir(parents=True,exist_ok=False)
    fixtures=out/"fixture"
    fixtures.mkdir()
    cases={c["id"]:c for c in json.loads((HERE/"cases.json").read_text("utf8"))}
    pairs=json.loads((HERE/"evidence/pairs.json").read_text("utf8"))
    jobs={"after-normal-1":("release","DS"),"after-award-1":("place","MiniMax"),"after-ask-2":("place","MiniMax")}
    for rid,(case,name) in jobs.items():
        row=next(r for r in pairs if (r["phase"],r["case"],r["provider"])==("after",case,name))
        exercise.write_line(fixtures/"wire.jsonl",{"result":"ds","turn":rid,"reply":[{"role":"assistant","content":row["content"]}]})
        receipt={"ok":True,"as_of":cases[case]["as_of"],"sources":cases[case]["sources"]}
        exercise.write_line(fixtures/"events.jsonl",{"payload":{"request_id":rid,"result":receipt}})
    exercise.F1=cases["release"]["question"]
    exercise.AWARD=cases["place"]["question"]
    exercise.CINEMA=cases["missing"]["question"]
    state=out/"core"
    args=SimpleNamespace(state=state,repo=HERE.parents[2],godot=godot,replay=fixtures,
                         budget=out/"disabled.sqlite",phase="after",cases=None)
    # exercise imports Core only after isolating its directories. Pin the same
    # as-of date on this side of that boundary as in the archived experiment.
    original_isolate=exercise.isolate
    def isolate_with_clock(path):
        original_isolate(path)
        from agent_core import public_search
        public_search.date=TrialDate
    exercise.isolate=isolate_with_clock
    try:
        asyncio.run(exercise.main(args))
    finally:
        exercise.isolate=original_isolate
    frames=lines(state/"frames.jsonl")
    window=lines(state/"window.jsonl")
    speech=lines(state/"tts.jsonl")
    rows=[]
    for frame in (f for f in frames if f["type"]=="chat.response"):
        rid=frame["request_id"]
        seen=next(w for w in window if w.get("request")==rid and w.get("type")=="chat.response")
        utterance,=[r["text"] for r in speech if r["request"]==rid and not r["narrating"]]
        assert seen["answer_visible"] and frame["text"] in seen["labels"] and seen["session"]==frame["conversationId"]
        if rid in jobs:
            case,name=jobs[rid]
            source=next(r for r in pairs if (r["phase"],r["case"],r["provider"])==("after",case,name))
            expected=source["delivery"]
            assert all(frame[k]==expected[k] for k in ("text","emotion","emotion_intensity","gesture"))
            assert [utterance]==expected["tts"]
        elif rid=="after-ask-1":
            assert "待确认" in frame["text"] and utterance==frame["text"]
        else:
            assert rid=="after-fault-1" and "密钥" in frame["text"] and utterance==frame["text"]
        rows.append({"request":rid,"session":seen["session"],"visible_label":frame["text"],"tts_input":utterance,
                     **{k:frame[k] for k in ("channel","emotion","emotion_intensity","gesture")}})
    with sqlite3.connect(args.budget) as db:
        assert db.execute("SELECT count(*) FROM attempts").fetchone()[0]==0
    assert len(rows)==5
    (out/"visible.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf8")
    print("VISIBLE_REPLAY_OK 5 actual labels and TTS inputs; zero external requests")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("out",type=lambda s:Path(s).resolve())
    p.add_argument("godot",type=lambda s:Path(s).resolve())
    args=p.parse_args()
    main(args.out,args.godot)
