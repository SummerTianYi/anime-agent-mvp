"""Apply, test and reverse the diagnostics patch in a disposable checkout of pinned main."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
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
        repo = Path(scratch) / "checkout"
        subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT), str(repo)], check=True)
        subprocess.run(["git", "checkout", "--quiet", "--detach", MAIN], cwd=repo, check=True)
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
        paths = [line.split(" b/", 1)[1] for line in patch.read_text("utf8").splitlines() if line.startswith("diff --git ")]
        original = {name: (repo / name).read_bytes() for name in paths}
        assert len(original) == 6
        for name,opts in (("clean_apply_check",["--check"]),("apply",[])):
            stats[name]=invoke(name,["git","apply","--unidiff-zero",*opts,str(patch)])
        for name,tree in (("main",repo),("candidate",ROOT)):
            stats[name+"_probe"]=invoke(name+"-probe",[sys.executable,"-B","-X","utf8",str(HERE/"slice_probe.py"),
                                        str(tree),str(args.out/(name+"-state")),name])
            log=(args.out/(name+"-probe.txt")).read_text("utf8").splitlines()
            stats[name+"_probe"]["authorization"]=json.loads(next(line.removeprefix("AUTH_PROBE ") for line in log if line.startswith("AUTH_PROBE ")))
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
        for name, opts in (("reverse_check", ["--check"]), ("reverse_apply", [])):
            invoke(name, ["git", "apply", "--unidiff-zero", "--reverse", *opts, str(patch)])
        assert all((repo / name).read_bytes() == raw for name, raw in original.items())
        invoke("tracked_clean", ["git", "diff", "--quiet", "HEAD", "--"])
        stats["rollback"] = {"patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
                             "byte_identical_files": len(original), "tracked_clean": True}
        (args.out/"result.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf8")
        print(stats["core"],stats["main_probe"],stats["candidate_probe"])


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("godot","assets","out"):
        p.add_argument(name,type=lambda s:Path(s).resolve())
    run(p.parse_args())
