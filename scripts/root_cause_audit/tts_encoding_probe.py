"""Codex: replay only the installed diagnostic print, not the GPU synthesizer."""
import argparse,ast,contextlib,hashlib,importlib.util,io,json,os,subprocess,sys
from pathlib import Path
from probe import ROOT,save
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);a=p.parse_args()
tts=a.production.parent/'tianyi-tts'
env=os.environ.copy()
for k in ('PYTHONUTF8','PYTHONIOENCODING'):env.pop(k,None)
identity=json.loads(subprocess.check_output([str(tts/'venv/Scripts/python.exe'),'-c','import sys,json;print(json.dumps(dict(encoding=sys.stdout.encoding,errors=sys.stdout.errors,utf8_mode=sys.flags.utf8_mode)))'],env=env,text=True))
spec=importlib.util.spec_from_file_location('audit_speech',a.production/'services/agent-core/agent_core/speech.py');speech=importlib.util.module_from_spec(spec);sys.modules[spec.name]=speech;spec.loader.exec_module(speech)
ev=json.loads((ROOT/'docs/assessments/root-cause-audit/evidence/desktop-10.json').read_text(encoding='utf-8'))
reply=next(m['content'] for m in ev['messages'] if m['role']=='assistant');parts=speech.split_reply_into_parts(reply)
source=tts/'GPT-SoVITS/GPT_SoVITS/inference_webui.py';tree=ast.parse(source.read_text(encoding='utf-8'))
stmt=next(n for n in ast.walk(tree) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='print' and '实际输入的目标文本:' in ast.unparse(n))
code=compile(ast.Module(body=[stmt],type_ignores=[]),str(source),'exec')
results=[]
for text in (parts[0],parts[1],'你好。','谢谢你😊。'):
    for encoding in (identity['encoding'],'utf-8'):
        raw=io.BytesIO();stream=io.TextIOWrapper(raw,encoding=encoding,errors='strict')
        try:
            with contextlib.redirect_stdout(stream):exec(code,{'text':text,'i18n':lambda s:s})
            stream.flush();status='printed'
        except UnicodeEncodeError as e:status='UnicodeEncodeError';error={'start':e.start,'end':e.end,'reason':e.reason}
        results.append({'text':text,'encoding':encoding,'result':status,**({'error':error} if status!='printed' else {})})
local=str(Path(os.environ['LOCALAPPDATA'])/'AnimeAgent/logs')
logs=Path('\\\\localhost\\'+local[0].lower()+'$\\'+local[3:])
observed=[]
for f in sorted(logs.glob('tts-20261007-*.stdout.log')):
    failures=[]
    for n,line in enumerate(f.read_bytes().decode('gbk',errors='replace').splitlines(),1):
        if 'TTS_SYNTH_FAILED' in line:
            prefix=line.split('TTS_SYNTH_FAILED')[0]
            failures.append({'line':n,'prefix_is_target_print':prefix.strip()=='实际输入的目标文本:','status':line[line.index('TTS_SYNTH_FAILED'):].strip()})
    if failures:observed.append({'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'failures':failures})
record={'layer':'offline counterfactual + passive runtime log; no synth/model/network calls',
 'source':'tianyi-tts/GPT-SoVITS/GPT_SoVITS/inference_webui.py','line':stmt.lineno,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'pipe_encoding_control':identity,'request_id':'avatar-chat-5937548','speech_parts':parts,'cases':results,'runtime_failure_log_metadata':observed,
 'limits':'Child probe proves Windows default pipe encoding, not an in-process sys.stdout inspection. Actual matching print prefix + UnicodeEncodeError separately corroborate. No production modification.'}
save('tts-encoding-counterfactual',record);print(json.dumps(record,ensure_ascii=False,indent=2))
