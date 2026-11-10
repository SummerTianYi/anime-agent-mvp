"""Replay the pinned baseline, preregistered implementation and candidate without network access."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "06ce15964ba0d9293d092e717b2eb38b48809416"
PREREG = "597372a6afa37c5035522a4632e6c7404fdc61d0"


def source_at(commit, dest):
    archive = subprocess.check_output(
        ["git", "archive", "--format=zip", commit, "services/agent-core/agent_core"], cwd=ROOT
    )
    with zipfile.ZipFile(io.BytesIO(archive)) as files:
        files.extractall(dest)
    return dest


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def verify(scratch):
    scratch.mkdir(parents=True, exist_ok=False)
    providers = HERE / "providers.json"
    rows = read(providers)
    cases = read(HERE / "cases.json")
    if ([row["slot"] for row in rows] != list(range(1, 13))
            or Counter((r["case"], r["provider"]) for r in rows)
            != Counter((case["id"], name) for case in cases for name in ("DS", "MiniMax"))
            or any(r["outcome"] != "received" for r in rows)):
        raise SystemExit("Provider archive is incomplete or has duplicate attempts.")
    for case in cases:
        hashes = {r["prompt_sha256"] for r in rows if r["case"] == case["id"]}
        if len(hashes) != 1:
            raise SystemExit(f"Model inputs differ for {case['id']}.")
    for name, commit, archive in (
        ("before", BASE, "before.json"), ("preregistered", PREREG, "after.json"),
        ("candidate", None, "after.json"),
    ):
        repo = source_at(commit, scratch / (name + "-source")) if commit else ROOT
        output = scratch / (name + ".json")
        command = [sys.executable, "-B", "-X", "utf8", str(HERE / "probe.py"), str(repo),
                   str(scratch / (name + "-state")), str(output)]
        if name != "before":
            command += ["--responses", str(providers)]
        subprocess.run(command, cwd=ROOT, check=True)
        actual = read(output)
        if actual != read(HERE / archive):
            raise SystemExit(f"{name} differs from {archive}. See {output}.")
        print(f"{name}: {sum(r['passed'] for r in actual)}/{len(actual)} match the task criteria", flush=True)
    print("PUBLIC_QUERY_REPLAY_OK")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("scratch", type=Path, help="A new directory. An existing directory is never reused.")
    verify(cli.parse_args().scratch.resolve())
