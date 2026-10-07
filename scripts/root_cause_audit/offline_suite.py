"""Codex: reuse existing tests in synthetic storage; never change V0/V1 evidence."""
import io,json,os,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for key in list(os.environ):
    if key.startswith(('ANIME_AGENT_','LLM_','GLM_','DEEPSEEK_')):
        del os.environ[key]
with tempfile.TemporaryDirectory(prefix='tianyi-audit-unit-') as tmp:
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(Path(tmp)/'absent.env'),
        ANIME_AGENT_DATA_DIR=tmp,ANIME_AGENT_TTS='0',ANIME_AGENT_WAKE_WORD='0',
        ANIME_AGENT_MCP_SERVERS='',LLM_PROVIDER='mock')
    sys.path.insert(0,str(ROOT/'services/agent-core'))
    from agent_core import main as core
    initial=core.memory
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'services/agent-core/tests'))
    ids=[]
    def collect(s):
        for item in s:
            if isinstance(item,unittest.TestSuite): collect(item)
            else: ids.append(item.id())
    collect(suite)
    start=time.monotonic()
    result=unittest.TextTestRunner(stream=stream,verbosity=1).run(suite)
    report=dict(layer='isolated existing regression; NOT desktop acceptance',
        tests=result.testsRun,seconds=round(time.monotonic()-start,3),ok=result.wasSuccessful(),
        ids=ids,failures=[dict(id=t.id(),detail=e) for t,e in result.failures+result.errors],
        skipped=[dict(id=t.id(),reason=r) for t,r in result.skipped])
    out=Path(os.environ.get('ANIME_AUDIT_OUT',str(ROOT/'docs/assessments/root-cause-audit/evidence')))/'offline-suite.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists(): raise SystemExit('No evidence overwrite')
    text=json.dumps(report,ensure_ascii=False,indent=2).replace(tmp,'{TEMP}').replace(str(ROOT),'{SOURCE}')
    out.write_text(text,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('ids','failures')},ensure_ascii=False))
    print('Failures:',[x['id'] for x in report['failures']])
    initial.close()
    raise SystemExit(not result.wasSuccessful())
