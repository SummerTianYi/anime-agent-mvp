"""Replay the archived visible choices through the DS response parser on final product code, with a hard network fence."""
import argparse
import asyncio
import json
import os
import socket
from pathlib import Path

import evaluate as ev


async def check(args):
    def deny(*unused, **kwargs):
        raise AssertionError("Offline replay attempted network I/O")
    socket.socket.connect=deny
    socket.socket.connect_ex=deny
    args.phase="archive"  # isolated synthetic adapter configuration, no credential
    core,_=ev.start_core(args)
    requests=ev.read_lines(args.evidence/"requests.jsonl")
    dialogues=ev.read_lines(args.evidence/"dialogues.jsonl")
    cases={}
    for group in ("daily","joy","low"):
        core.memory.close()
        core.memory=core.MemoryStore(args.state / group)
        sid=core.memory.create_session()["id"]
        core._action_ledger=None
        core._actions()
        events=[]
        async def collect(roles,event):
            if event["type"]=="chat.response":
                events.append(event["text"])
        core.hub.send_roles=collect
        for idx,text in enumerate(ev.SCENES[group],1):
            tag=f"after-{group}-{idx}"
            original=next(x for x in dialogues if x["id"]==tag)
            req=next(x for x in requests if x["phase"]=="request" and x["turn"]==tag)
            result=next(x for x in requests if x["phase"]=="result" and x["n"]==req["n"])
            matching=[]
            ignoring_breaks=[]
            def historical_breaks(body):
                import copy
                normalized=copy.deepcopy(body)
                for m in normalized["messages"]:
                    if m["role"] == "assistant":
                        parsed=json.loads(m["content"])
                        parsed["reply"]=parsed["reply"].replace("\n","")
                        m["content"]=ev.encoded(parsed)
                return normalized
            def replay(request):
                expected=json.loads(request.data)
                matching.append(ev.sha(ev.encoded(expected))==req["body_sha256"])
                ignoring_breaks.append(historical_breaks(expected)==historical_breaks(req["body"]))
                return json.dumps({"choices":result["choices"]},ensure_ascii=False).encode()
            core.provider._request=replay
            events.clear()
            await core.handle_chat(text,f"t-{group}-{idx}",sid,effort="deep")
            previous=[e["text"] for e in original["bubbles"]]
            cases[tag]={"same_request":matching==[True],"request_equivalent_except_historical_breaks":ignoring_breaks==[True],
                        "same_bubbles":events==previous,"same_words_and_punctuation":[s.replace("\n","") for s in events]==[s.replace("\n","") for s in previous],
                        "final_bubbles":list(events)}
    core.memory.close()
    ev.save(args.state/"final-wire-equivalence.json",cases)
    return all(row["request_equivalent_except_historical_breaks"] and row["same_words_and_punctuation"] for row in cases.values())


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("repo","evidence","state"):
        p.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args()
    if not (args.state/"synthetic-only").is_file() or args.state.resolve().is_relative_to(args.repo.resolve()):
        p.error("Use a dedicated marked scratch outside the checkout")
    raise SystemExit(0 if asyncio.run(check(args)) else 1)
