"""Build a content-addressed, credential-free record or verify the committed record offline."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

HERE=Path(__file__).resolve().parent
RUNS={"before":"before","first-fix":"after","live-f1":"final-normal","live-other":"final-other",
      "render-f1":"visible-f1","render-other":"visible-other"}


def lines(path):
    return [json.loads(l) for l in path.read_text(encoding="utf8").splitlines()] if path.exists() else []


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def public_receipt(receipt):
    record={k:v for k,v in receipt.items() if k in {"ok","outcome","kind","as_of","failures","error","local_time","weekday","action_id"}}
    if receipt.get("sources"):
        record["sources"]=[{"title":s["title"],"url":s["url"],"field":s.get("field",""),
                            "text_sha256":digest(s["content"])} for s in receipt["sources"]]
    return record


def snapshot(d):
    texts={}
    def ref(value):
        k=digest(value)
        texts[k]=value
        return k
    turns=lines(d/"turns.jsonl")
    windows=lines(d/"window.jsonl")
    voices=lines(d/"tts.jsonl")
    actions=lines(d/"events.jsonl")
    dispatches=lines(d/"dispatch.jsonl")
    out=[]
    for t in turns:
        rid=t["request"]
        actual=next(f for f in lines(d/"frames.jsonl") if f["type"]=="chat.response" and f["request_id"]==rid)
        assert actual["text"]==t["text"] and actual["conversationId"]==t["session"]
        row={k:v for k,v in t.items() if k!="text"}
        row["bubble"]=ref(actual["text"])
        row["window"]=[{"type":x["type"],"status":x["status"],"session":x["session"],"labels":[ref(h) for h in x["labels"]],
                        **({"answer_visible":x["answer_visible"]} if "answer_visible" in x else {})}
                        for x in windows if x.get("request")==rid]
        row["tts"]=[ref(s["text"]) for s in voices if s["request"]==rid and not s["narrating"]]
        row["dispatch"]=[a for a in dispatches if a["request"]==rid]
        row["events"]=[]
        for event in actions:
            src=event["payload"]
            if src.get("request_id")!=rid:
                continue
            item={k:v for k,v in src.items() if k in {"rule_id","kind","allowed","tool","arguments","task_id",
                  "action_id","revision","args_hash","outcome","source","result_ref","actions"}}
            if "result" in src:
                item["result"]=public_receipt(src["result"])
            row["events"].append({"type":event["type"],**item})
        out.append(row)
    return {"origin":lines(d/"isolation.jsonl")[0],"turns":out,"texts":texts,
            "other_speech_entry":[s for s in voices if s["request"] not in {t["request"] for t in turns}]}


def pack(state, out):
    out.mkdir(parents=True,exist_ok=False)
    def save(name,data):
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    wire=[]
    for label,folder in RUNS.items():
        save(label+".json",snapshot(state/folder))
        if not label.startswith("render"):
            wire.extend({"run":label,**r} for r in lines(state/folder/"wire.jsonl"))
    (out/"requests.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in wire),encoding="utf8")
    with sqlite3.connect(f"file:{(state/'budget.sqlite').as_posix()}?mode=ro",uri=True) as db:
        attempts=db.execute("SELECT id,kind,phase,turn,body_hash FROM attempts ORDER BY id").fetchall()
    save("budget.json",attempts)
    save("godot.json",json.loads((state/"godot-final/gates.json").read_text(encoding="utf8")))


def verify(path):
    attempts=json.loads((path/"budget.json").read_text(encoding="utf8"))
    wires=lines(path/"requests.jsonl")
    calls=[r for r in wires if "kind" in r]
    assert len(attempts)==len(calls) and [(r["kind"],r["turn"],r["sha256"]) for r in calls]==[(r[1],r[3],r[4]) for r in attempts]
    assert all(r["fields"]["model"]=="deepseek-flash" for r in calls if r["kind"]=="ds")
    assert all(r["n"]==i for kind in ("ds","search") for i,r in enumerate((c for c in calls if c["kind"]==kind),1))
    assert sum(r["kind"]=="ds" for r in calls)<=24 and sum(r["kind"]=="search" for r in calls)<=8
    count=0
    for label in RUNS:
        data=json.loads((path/(label+".json")).read_text(encoding="utf8"))
        texts=data["texts"]
        assert all(digest(value)==k for k,value in texts.items())
        for row in data["turns"]:
            observed=[w for w in row["window"] if w["type"]=="chat.response" and w["session"]==row["session"]]
            assert observed and row["bubble"] in observed[-1]["labels"] and len(row["tts"])==1
            body,voice=texts[row["bubble"]],texts[row["tts"][0]]
            if label.startswith(("live","render")):
                for token in ("mcp__","result_ref","执行记录","args_hash","Traceback","get_time"):
                    assert token not in body and token not in voice
            if label.startswith("render"):
                assert observed[-1]["answer_visible"]
                assert "https://" not in voice
                if "来源：\n" in body:
                    assert voice.startswith(body.partition("来源：\n")[0]) and "来源是" in voice
                else:
                    assert body==voice
            count+=1
    print(f"VERIFIED {count} correlated turns; {len(calls)} metered external requests")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack",type=Path,help="Private raw run directory")
    parser.add_argument("--out",type=Path,default=HERE/"evidence")
    args=parser.parse_args()
    if args.pack:
        pack(args.pack,args.out)
    verify(args.out)
