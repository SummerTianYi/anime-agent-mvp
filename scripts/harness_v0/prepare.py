"""Freeze the current source overlay and exact non-secret provider configuration."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import io

BASE = "d3ed6d68f2509ad51bea15cf8224c5f3a165d957"
CORE = "services/agent-core/"


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL)


def capture(source, destination, env_path):
    from dotenv import dotenv_values
    values = dotenv_values(env_path)
    assert git(source, "rev-parse", "HEAD").decode().strip() == BASE, "Unexpected reference HEAD"
    names = git(source, "ls-files", CORE + "agent_core").decode().splitlines()
    names += [CORE + "agent_core/provider_http.py"]
    overlay, hashes = {}, {}
    for name in sorted(set(names)):
        file = source / name
        if not file.is_file():
            continue
        content = file.read_text(encoding="utf-8")
        hashes[name] = sha(content)
        try:
            original = git(source, "show", BASE + ":" + name).decode("utf-8").replace("\r\n", "\n")
        except subprocess.CalledProcessError:
            original = None
        if original != content:
            overlay[name] = {"base_sha256": sha(original) if original is not None else None, "text": content}
    h = (source / (CORE + "agent_core/harness.py")).read_text(encoding="utf-8")
    prompt = next(ast.literal_eval(n.value) for n in ast.parse(h).body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "ACTIVE_PROMPT_OVERRIDE" for t in n.targets))
    assert values.get("GLM_CREDENTIAL_SOURCE") == "deepseek", "Use verified shared WeChat config"
    models = {}
    for tag, variable in (("ds", "DEEPSEEK_MODEL"), ("glm", "GLM_MODEL")):
        assert values.get(variable) and values.get("DEEPSEEK_BASE_URL") and values.get("DEEPSEEK_API_KEY")
        models[tag] = {"model": values[variable], "base_url": values["DEEPSEEK_BASE_URL"].rstrip("/"),
                       "protocol": "openai-chat-completions", "stream": False,
                       "temperature": "omitted/current adapter default", "seed": "not supported/omitted",
                       "thinking": "omitted/current adapter default", "tool_choice": "auto when tools present",
                       "timeout_seconds": float(values.get("LLM_TIMEOUT_SECONDS") or 45),
                       "proxy_mode": values.get("LLM_PROXY_MODE") or "auto",
                       "credential_reference": "DEEPSEEK_API_KEY (value excluded)"}
    out = destination / "evidence/baseline"
    dump(out / "runtime_overlay.json", overlay)
    (out / "current_prompt.txt").write_text(prompt, encoding="utf-8")
    manifest = {"reference_sha": BASE, "source_sha": BASE, "source_dirty": True,
                "source_identity": "reference SHA + normalized UTF-8 source manifest + runtime overlay",
                "files": hashes, "source_tree_sha256": sha(json.dumps(hashes, sort_keys=True)),
                "current_prompt_sha256": sha(prompt),
                "overlay_sha256": sha((out / "runtime_overlay.json").read_bytes()), "models": models,
                "initial_tracked_diff": git(source, "diff", "--name-only").decode().splitlines()}
    dump(out / "manifest.json", manifest)
    return manifest


def materialize(repo, package, target):
    manifest = json.loads((package / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))
    archive = git(repo, "archive", manifest["reference_sha"], CORE + "agent_core")
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            path = target / member.name
            if member.isfile():
                assert path.resolve().is_relative_to(target.resolve())
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tar.extractfile(member).read())
    overlay_path = package / "evidence/baseline/runtime_overlay.json"
    assert sha(overlay_path.read_bytes()) == manifest["overlay_sha256"]
    for name, item in json.loads(overlay_path.read_text(encoding="utf-8")).items():
        path = target / name
        assert path.resolve().is_relative_to(target.resolve())
        if item["base_sha256"] is not None:
            assert sha(path.read_text(encoding="utf-8")) == item["base_sha256"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item["text"], encoding="utf-8")
    for name, expected in manifest["files"].items():
        assert sha((target / name).read_text(encoding="utf-8")) == expected, name
    return target / CORE
