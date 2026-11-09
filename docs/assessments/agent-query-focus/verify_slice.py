"""Extract pinned main without its local assets/config. Apply and exercise only the review patch."""
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/"agent-query-delivery"))
import godot_checks

MAIN="cf62b484ca8f075d97c2d4c41496480c7c82501c"


def run(args):
    args.out.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="ty-slice-") as scratch:
        repo=Path(scratch)
        raw=subprocess.check_output(["git","archive",MAIN],cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(repo, filter="data")
        def invoke(key, command, *, ok=True, input_bytes=None):
            result=subprocess.run(command,cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,input=input_bytes)
            lines=result.stdout.decode("utf8","replace").splitlines()
            (args.out/(key+".txt")).write_text("\n".join(lines),encoding="utf8")
            if (result.returncode==0)!=ok:
                raise RuntimeError(key+" unexpected status "+str(result.returncode))
            return {"exit":result.returncode,"last":lines[-1] if lines else ""}
        stats={}
        # Check the historical complete Core patch, independently of whether the UI subset applies.
        core_patch=subprocess.check_output(["git","diff","8025c6b","4df20e7","--","services/agent-core/agent_core"],cwd=ROOT)
        stats["full_candidate_on_main"]=invoke("core-check",["git","apply","--check","-"],ok=False,input_bytes=core_patch)
        patch=HERE/"main-diagnostics.patch"
        for name,opts in (("clean_apply_check",["--check"]),("apply",[])):
            stats[name]=invoke(name,["git","apply","--unidiff-zero",*opts,str(patch)])
        stats["diagnostic_probe"]=invoke("probe",[sys.executable,"-B","-X","utf8",str(HERE/"slice_probe.py"),str(repo),str(args.out/"probe-state")])
        # Keep the repository's historical suite unchanged in this disposable copy.
        checks=repo/"docs/assessments/agent-query-delivery/checks.py"
        checks.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(HERE.parent/"agent-query-delivery/checks.py",checks)
        stats["core"]=invoke("core",[sys.executable,"-B","-X","utf8",str(checks),str(args.out/"c")])
        godot_checks.ROOT=repo
        godot_checks.GATES={k:v for k,v in godot_checks.GATES.items() if k in {"verify_text_input","verify_tool_activity"}}
        passed=godot_checks.run(SimpleNamespace(godot=args.godot,assets=args.assets,out=args.out/"godot"))
        stats["godot"]=json.loads((args.out/"godot/gates.json").read_text("utf8"))
        assert passed
        (args.out/"result.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf8")
        print(stats["core"],stats["diagnostic_probe"])


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("godot","assets","out"):
        p.add_argument(name,type=lambda s:Path(s).resolve())
    run(p.parse_args())
