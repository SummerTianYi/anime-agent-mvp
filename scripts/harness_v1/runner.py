"""V1 frozen dual-model trials. Synthetic data only; append-only batch evidence."""
import argparse, ast, json, os, shutil, sqlite3, subprocess, sys, tempfile, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from scripts.harness_v0.budget import initialize
from scripts.harness_v0.gateway_probe import credentials
from scripts.harness_v0.prepare import dump, sha
from scripts.harness_v0.redact_titles import clean
from .grader import grade

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=ROOT/"docs/assessments/harness-v1"

def freeze():
    old=ROOT/"docs/assessments/harness-v0/cases.json"
    target=PACKAGE/"cases.json"
    spec=json.loads(old.read_text(encoding="utf-8"))
    spec.update(version="v1.0",parent_cases_sha256=sha(old.read_bytes()))
    spec["budget"].update(hard_http_limit=1100,max_seconds_per_trial=240,parallel_model_workers=1)
    spec["grading_rules"]["v1"]="Same outcome assertions, calibrated semantic equivalence and exact native ticket/receipt binding. No weakened artifact criteria."
    if not target.exists():
        dump(target,spec)
    paths=sorted((ROOT/"services/agent-core/agent_core").glob("*.py"))
    paths+=sorted((ROOT/"scripts/harness_v1").glob("*.py"))
    paths += [ROOT/"apps/avatar-runtime/runtime.gd",ROOT/"apps/avatar-runtime/interaction_ui.gd"]
    files={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in paths}
    h=ast.parse((ROOT/"services/agent-core/agent_core/harness.py").read_text(encoding="utf-8"))
    parts={}
    for node in h.body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant):
            for t in node.targets:
                if isinstance(t,ast.Name): parts[t.id]=node.value.value
    prompt=parts["ROLE_PROMPT"]+"\n\n"+parts["RUNTIME_CONTRACT"]
    return dict(harness_version="v1",files=files,source_tree_sha256=sha(json.dumps(files,sort_keys=True)),
                current_prompt_sha256=sha(prompt),case_sha256=sha(target.read_bytes()),
                parent_source_sha="559404f29ca255448f490615f5e52cb27dc58d3e",
                source_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                source_dirty=True,source_identity="source_sha + exact file manifest (all files committed with this batch)")

def run(envfile,batch,selected):
    key,models=credentials(envfile)
    versions=freeze()
    batch=PACKAGE/"batches"/batch
    assert not batch.exists(),"Append-only: use a new batch"
    batch.mkdir(parents=True)
    cases=json.loads((PACKAGE/"cases.json").read_text(encoding="utf-8"))["cases"]
    if selected: cases=[c for c in cases if c["id"] in selected.split(",")]
    slots=[(c,tag,repeat) for c in cases for repeat in range(1,4) for tag in ("ds","glm")]
    dump(batch/"registration.json",dict(registered_utc=datetime.now(timezone.utc).isoformat(),
        versions=versions,models=models,slots=[f"{tag}-{c['id']}-r{n}" for c,tag,n in slots],
        http_cap=1100,per_trial_http=20,max_turns=6,max_seconds=240,external_services_tested=False))
    budget=PACKAGE/"http-budget.private.sqlite3"
    initialize(budget,1100)
    stopped=None; consecutive=0
    with tempfile.TemporaryDirectory(prefix="tianyi-v1-eval-") as temp:
        temp=Path(temp); source=temp/"source"
        shutil.copytree(ROOT/"services/agent-core/agent_core",source/"agent_core",
                        ignore=shutil.ignore_patterns("__pycache__"))
        env=os.environ.copy();env.update(HARNESS_MODEL_KEY=key,PYTHONUTF8="1",PYTHONIOENCODING="utf-8")
        with (batch/"results.jsonl").open("x",encoding="utf-8") as sink:
            for case,tag,n in slots:
                trial=f"{batch.name}-{tag}-{case['id']}-r{n}"
                if stopped:
                    ev=dict(trial_id=trial,case_id=case["id"],blocked=stopped,attempted=False,
                        turns=[],events=[],executions=[],http=[],before={"files":case["initial_fixture"]["files"]},
                        after={"files":case["initial_fixture"]["files"]},source_manifest=versions)
                else:
                    work=temp/trial;work.mkdir()
                    job=dict(case=case,model_tag=tag,trial_id=trial,trial_dir=str(work),
                        source_path=str(source),model=models[tag],versions=versions,budget_path=str(budget),
                        fixture_script=str(ROOT/"scripts/harness_v0/fixture_mcp.py"),output=str(work/"output.json"))
                    dump(work/"job.json",job)
                    try:
                        p=subprocess.run([sys.executable,"-m","scripts.harness_v1.wire_worker",str(work/"job.json")],
                            cwd=ROOT,env=env,capture_output=True,text=True,encoding="utf-8",timeout=300)
                        if p.returncode or not Path(job["output"]).exists():
                            raise RuntimeError("worker_failed:"+str(p.returncode)+":"+sha(p.stderr))
                        ev=json.loads(Path(job["output"]).read_text(encoding="utf-8"));ev["attempted"]=True
                    except Exception as exc:
                        ev=dict(trial_id=trial,case_id=case["id"],blocked="evaluation_worker_failed",attempted=True,
                            turns=[],events=[],executions=[],http=[],before={"files":case["initial_fixture"]["files"]},
                            after={"files":case["initial_fixture"]["files"]},diagnostic=str(exc),
                            source_manifest=versions)
                        stopped="evaluation_worker_failed"
                    consecutive=consecutive+1 if ev.get("blocked") else 0
                    if ev.get("wire_gate",{}).get("halted_status") or consecutive>=3 or ev.get("blocked")=="global_http_limit":
                        stopped=ev.get("blocked","repeated_external_failure")
                score=grade(case,ev)
                changes=[]; redacted=clean(ev,changes=changes)
                assert grade(case,redacted)==score
                path=batch/"evidence"/(trial+".json")
                redacted.update(grade=score,redaction_changes=changes)
                dump(path,redacted)
                with sqlite3.connect(budget) as db:
                    calls=[{"sequence":a,"trial_id":b} for a,b in db.execute("SELECT * FROM calls ORDER BY id")]
                count=sum(x["trial_id"]==trial for x in calls)
                dump(PACKAGE/"http-accounting.json",{"cap":1100,"http_calls":len(calls),"attempts":calls})
                row=dict(trial_id=trial,model_tag=tag,case_id=case["id"],repeat=n,
                    model_configuration=models[tag],versions=versions,layer="real-model/isolated-core/controlled-mcp",
                    attempted=ev["attempted"],verdict=score["verdict"],reasons=score["reasons"],
                    elapsed_ms=ev.get("elapsed_ms"),http_calls=count,evidence_path=path.relative_to(PACKAGE).as_posix(),
                    evidence_sha256=sha(path.read_bytes()),external_services_tested=False)
                sink.write(json.dumps(row,ensure_ascii=False)+"\n");sink.flush()
                print(trial,row["verdict"],"HTTP",count,row["reasons"],flush=True)
    replay(batch)
def replay(batch):
    registration=json.loads((batch/"registration.json").read_text(encoding="utf-8"))
    cases={c["id"]:c for c in json.loads((PACKAGE/"cases.json").read_text(encoding="utf-8"))["cases"]}
    assert sha((PACKAGE/"cases.json").read_bytes())==registration["versions"]["case_sha256"]
    rows=[json.loads(l) for l in (batch/"results.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in rows:
        p=PACKAGE/row["evidence_path"]
        assert sha(p.read_bytes())==row["evidence_sha256"]
        result=grade(cases[row["case_id"]],json.loads(p.read_text(encoding="utf-8")))
        assert result["verdict"]==row["verdict"] and result["reasons"]==row["reasons"]
    summary={tag:dict(scheduled=sum(r["model_tag"]==tag for r in rows),
              actual_runs=sum(r["attempted"] for r in rows if r["model_tag"]==tag),
              verdicts=dict(Counter(r["verdict"] for r in rows if r["model_tag"]==tag)),
              http_calls=sum(r["http_calls"] for r in rows if r["model_tag"]==tag)) for tag in ("ds","glm")}
    dump(batch/"summary.json",summary);print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("operation",choices=["run","replay"])
    p.add_argument("--env-file",type=Path);p.add_argument("--batch",default="core-01");p.add_argument("--cases",default="")
    a=p.parse_args()
    if a.operation=="run":run(a.env_file,a.batch,a.cases)
    else:replay(PACKAGE/"batches"/a.batch)
