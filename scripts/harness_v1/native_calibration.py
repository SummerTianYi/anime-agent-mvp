"""Adversarial grader calibration for V1 native receipt binding."""
import copy,json
from pathlib import Path
from .grader import grade
from scripts.harness_v0.prepare import dump
root=Path(__file__).resolve().parents[2]
package=root/"docs/assessments/harness-v1"
case=next(c for c in json.loads((package/"cases.json").read_text(encoding="utf-8"))["cases"] if c["id"]=="F02")
sample=package/"batches/core-01/evidence/core-01-ds-F02-r1.json"
original=json.loads(sample.read_text(encoding="utf-8"))
tests=[]
def test(name,ev,want):
    score=grade(case,ev)
    got=all(c["passed"] for c in score["checks"] if c["criterion"].startswith(("no_execution_without_bound","durable_correlated_receipt")))
    tests.append(dict(name=name,passed=got==want,actual=got,expected=want))
test("real successful artifact and native receipt",original,True)
for field,value in (("action_id","wrong-action"),("revision",999),("args_hash","wrong-digest"),("arguments",{"path":"wrong","content":"wrong"})):
    ev=copy.deepcopy(original)
    next(x for x in ev["executions"] if x["kind"]=="mutation")["native_action"][field]=value
    test("forged "+field,ev,False)
ev=copy.deepcopy(original)
next(x for x in ev["executions"] if x["kind"]=="mutation")["authorized_by"]="unrelated-turn"
test("wrong confirmation request",ev,False)
ev=copy.deepcopy(original)
ev["after"]["database"]["harness_actions"]=[]
test("missing durable receipt",ev,False)
dump(package/"evidence/calibration/native-receipts.json",dict(tests=tests,passed=all(t["passed"] for t in tests),
      source_sample=sample.relative_to(root).as_posix()))
print(json.dumps({"tests":len(tests),"passed":all(t["passed"] for t in tests)}))
raise SystemExit(not all(t["passed"] for t in tests))
