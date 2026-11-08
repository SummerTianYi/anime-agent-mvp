"""Read launch metadata and public config fields, plus disk fingerprints. No production conversation queries."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
import psutil

here = Path(__file__).resolve().parent
repo = here.parents[2]
live = json.loads((here / "runtime.json").read_text(encoding="utf-8-sig"))
p = psutil.Process(live["core"]["pid"])
prod = Path(p.cwd()).parents[1]
base_main = Path(sys.argv[1])
assert p.cmdline()[-2:] == ["-m", "agent_core.main"]
assert (prod / "services/agent-core").resolve() == Path(p.cwd()).resolve()
env = p.environ()
def fields(source):
    model = source.get("DEEPSEEK_MODEL")
    return {"model":model if model == "deepseek-flash" else "unknown",
            "host":urlsplit(source.get("DEEPSEEK_BASE_URL", "")).hostname,
            "llm_provider":source.get("LLM_PROVIDER") if source.get("LLM_PROVIDER")=="deepseek" else "unknown",
            "timeout_seconds":source.get("LLM_TIMEOUT_SECONDS") if source.get("LLM_TIMEOUT_SECONDS","").isdigit() else None,
            "proxy_mode":source.get("LLM_PROXY_MODE") if source.get("LLM_PROXY_MODE") in ("direct","auto","system") else None}
def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()
def snapshot(root):
    folder = root / "services/agent-core/agent_core"
    src = (folder/"harness.py").read_text(encoding="utf-8")
    literals = {n.targets[0].id:n.value.value for n in ast.parse(src).body if isinstance(n,ast.Assign)
                and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)}
    composed = literals["ROLE_PROMPT"] + "\n\n" + literals["RUNTIME_CONTRACT"]
    return {"git_HEAD":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
            "lf_source_sha256":{f:digest((folder/f).read_text(encoding="utf-8")) for f in
                ("main.py","harness.py","agent_loop.py","storage.py","memory_retrieval.py")},
            "disk_active_prompt_sha256":digest(composed), "harness_mtime_utc_epoch":(folder/"harness.py").stat().st_mtime,
            "contains_v12_trust_clause":"互相信任的长期伙伴" in composed}
data = {"runtime":live,"process_cwd":"<formal-checkout>/services/agent-core",
        "process_created_epoch":p.create_time(),"module_entry":"-m agent_core.main",
        "formal_checkout_locator":"2026-08-28/https-github-com-summertianyi-anime-agent/work/anime-agent-mvp",
        "process_env_allowlist":fields(env), "production_disk":snapshot(prod),"candidate_disk":snapshot(repo),
        "test_adapter_lf_sha256":digest(base_main.read_text(encoding="utf-8")),
        "process_in_memory_prompt_sha256":None, "production_last_wire_body":None,"production_ui_effort":None,
        "test_effort":"deep","test_model_thinking":"disabled (observed wire)", "test_mcp_servers":0}
(here/"versions.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("runtime evidence recorded",fields(env))
