"""One fixed, interleaved 2 x 2 x 3 live experiment. No search, retries or tool access."""
import argparse
import json
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENDPOINTS = {"DS":("https://api.deepseek.com/chat/completions","deepseek-flash","DEEPSEEK_API_KEY"),
             "MiniMax":("https://api.minimax.cn/v1/chat/completions","MiniMax-M3.1-Flash","MINIMAX_API_KEY")}
SHARED = {"stream":False,"max_tokens":4096,"temperature":1,"top_p":0.95}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


def setting(path, wanted):
    for line in path.read_text("utf-8-sig").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == wanted:
            return value.strip().strip("'\"")
    return ""


def experiment(args):
    cases = json.loads((HERE / "cases.json").read_text("utf8"))
    prompts = {phase:{r["case"]:r for r in json.loads((args.state / (phase+".json")).read_text("utf8"))}
               for phase in ("before","after")}
    db = sqlite3.connect(args.state/"pairs.sqlite")
    db.execute("CREATE TABLE IF NOT EXISTS attempts (slot INTEGER PRIMARY KEY, record TEXT NOT NULL)")
    keys = {name:setting(args.ds if name=="DS" else args.minimax, v[2]) for name,v in ENDPOINTS.items()}
    if not all(keys.values()):
        raise SystemExit("A configured key is missing.")
    if setting(args.ds,"DEEPSEEK_MODEL") != ENDPOINTS["DS"][1]:
        raise SystemExit("Configured DS model differs from the protocol.")
    slot = 0
    try:
        for index, case in enumerate(cases):
            for phase in (("before","after") if index%2==0 else ("after","before")):
                for name in (("DS","MiniMax") if slot%4==0 else ("MiniMax","DS")):
                    slot += 1
                    current = prompts[phase][case["id"]]
                    url, model, _ = ENDPOINTS[name]
                    record = {"slot":slot,"provider":name,"phase":phase,"case":case["id"],"model":model,
                              "prompt_sha256":current["prompt_sha256"],"outcome":"reserved"}
                    # An interrupted slot cannot be sent twice, including on a second invocation.
                    if db.execute("SELECT 1 FROM attempts WHERE slot=?",(slot,)).fetchone():
                        continue
                    assert slot <= 12
                    with db:
                        db.execute("INSERT INTO attempts VALUES (?,?)",(slot,json.dumps(record)))
                    body = {**SHARED, "model":model,"messages":current["messages"]}
                    payload = json.dumps(body,ensure_ascii=False).encode()
                    request = urllib.request.Request(url,data=payload,headers={
                        "Content-Type":"application/json","Authorization":"Bearer "+keys[name]},method="POST")
                    started = time.monotonic()
                    try:
                        with urllib.request.build_opener(NoRedirect()).open(request,timeout=90) as reply:
                            result = json.load(reply)
                        candidate = result["choices"][0]
                        content = candidate["message"]["content"]
                        if not isinstance(content,str) or not content.strip() or candidate.get("finish_reason")!="stop":
                            raise ValueError("incomplete content")
                        record.update(outcome="received",content=content,usage=result.get("usage"),served_model=result.get("model"))
                    except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
                        record.update(outcome="failed",error=type(exc).__name__,http=getattr(exc,"code",None))
                    record["elapsed_seconds"] = round(time.monotonic()-started,3)
                    with db:
                        db.execute("UPDATE attempts SET record=? WHERE slot=?",(json.dumps(record,ensure_ascii=False),slot))
                    print(slot,phase,name,record["outcome"],flush=True)
                    if record.get("http") in (401,403,429):
                        return
    finally:
        rows=[json.loads(r[0]) for r in db.execute("SELECT record FROM attempts ORDER BY slot")]
        (args.state/"responses.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf8")
        db.close()


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("state","ds","minimax"):
        parser.add_argument(arg,type=Path)
    experiment(parser.parse_args())
