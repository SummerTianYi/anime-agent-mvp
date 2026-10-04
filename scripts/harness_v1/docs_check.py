"""Offline doc guard and shared-prompt export, without production import/data."""
import ast,json,os,runpy,sys,tempfile
from pathlib import Path
from scripts.harness_v0.prepare import dump,sha
ROOT=Path(__file__).resolve().parents[2]
tree=ast.parse((ROOT/"services/agent-core/agent_core/harness.py").read_text(encoding="utf-8"))
parts={}
for n in tree.body:
    if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant):
        for t in n.targets:
            if isinstance(t,ast.Name):parts[t.id]=n.value.value
prompt=parts["ROLE_PROMPT"]+"\n\n"+parts["RUNTIME_CONTRACT"]
(ROOT/"docs/assessments/harness-v1/shared-prompt.txt").write_text(prompt,encoding="utf-8",newline="\n")
with tempfile.TemporaryDirectory(prefix="tianyi-doc-guard-") as tmp:
    for k in list(os.environ):
        if k.startswith(("ANIME_AGENT_","LLM_","GLM_","DEEPSEEK_")):del os.environ[k]
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(Path(tmp)/"none.env"),ANIME_AGENT_DATA_DIR=tmp,
                      LLM_PROVIDER="mock",ANIME_AGENT_TTS="0",ANIME_AGENT_WAKE_WORD="0",ANIME_AGENT_MCP_SERVERS="")
    sys.path.insert(0,str(ROOT/"services/agent-core"))
    from agent_core import main
    try:
        module=runpy.run_path(str(ROOT/"scripts/check_docs_consistency.py"),run_name="guard")
        code=module["main"]()
    finally:main.memory.close()
    raise SystemExit(code)
