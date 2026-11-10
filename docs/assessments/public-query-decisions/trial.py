"""Submit the six captured native tool requests once per configured model. No search or retries."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"agent-query-focus"))
from compare import ENDPOINTS, SHARED, NoRedirect, setting


def main(args):
    requests = json.loads((args.state/"prompts.json").read_text("utf8"))
    cases = json.loads((HERE/"cases.json").read_text("utf8"))
    assert len(requests)==len(cases)==6 and [r["case"] for r in requests]==[c["id"] for c in cases]
    keys = {k:setting(args.ds if k=="DS" else args.minimax,cfg[2]) for k,cfg in ENDPOINTS.items()}
    if not all(keys.values()) or setting(args.ds,"DEEPSEEK_MODEL")!=ENDPOINTS["DS"][1]:
        raise SystemExit("Required existing provider settings unavailable.")
    db = sqlite3.connect(args.state/"attempts.sqlite")
    db.execute("CREATE TABLE IF NOT EXISTS attempts (slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 1 AND 12), data TEXT NOT NULL)")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        for index, request in enumerate(requests):
            for position, name in enumerate(("DS","MiniMax") if index%2==0 else ("MiniMax","DS")):
                slot=1+2*index+position
                row={"slot":slot,"case":request["case"],"provider":name,"model":ENDPOINTS[name][1],
                     "prompt_sha256":request["hash"],"outcome":"reserved"}
                with db:
                    added=db.execute("INSERT OR IGNORE INTO attempts VALUES(?,?)",(slot,json.dumps(row))).rowcount
                if not added:
                    continue
                body={**SHARED,"model":row["model"],"messages":request["messages"],"tools":request["tools"],"tool_choice":"auto"}
                wire=urllib.request.Request(ENDPOINTS[name][0],data=json.dumps(body,ensure_ascii=False).encode(),
                       headers={"Content-Type":"application/json","Authorization":"Bearer "+keys[name]},method="POST")
                started=time.monotonic()
                try:
                    with opener.open(wire,timeout=60) as response:
                        result=json.load(response)
                    choice=result["choices"][0]
                    raw=choice["message"]
                    # Only the native proposal reaches the host; do not archive hidden model reasoning.
                    row.update(outcome="received",message={"role":"assistant","content":None,"tool_calls":raw.get("tool_calls",[])},
                               finish_reason=choice.get("finish_reason"),served_model=result.get("model"),usage=result.get("usage"))
                except (OSError,ValueError,KeyError,IndexError,TypeError) as exc:
                    row.update(outcome="failed",error=type(exc).__name__,http=getattr(exc,"code",None))
                row["elapsed_seconds"]=round(time.monotonic()-started,3)
                with db:
                    db.execute("UPDATE attempts SET data=? WHERE slot=?",(json.dumps(row,ensure_ascii=False),slot))
                print(slot,name,row["case"],row["outcome"],flush=True)
                if row.get("http") in (401,403,429):
                    return
    finally:
        rows=[json.loads(r[0]) for r in db.execute("SELECT data FROM attempts ORDER BY slot")]
        args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        db.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("state","ds","minimax","output"):
        parser.add_argument(arg,type=Path)
    main(parser.parse_args())
