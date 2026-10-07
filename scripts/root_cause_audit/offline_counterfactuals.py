"""Codex: synthetic causal probes; no live Core, model, connector or user DB."""
import ast,asyncio,copy,hashlib,io,json,os,sqlite3,sys,tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from probe import ROOT,save
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'services/agent-core'))
from agent_core.storage import MemoryStore,_fact_similarity
from agent_core.memory_retrieval import retrieve_relevant
from agent_core import tools
from scripts.harness_v1.grader import grade,false_completion,normalize_facts

findings=[]
def add(id,**kw):findings.append(dict(id=id,**kw))
def memory():
    obj=MemoryStore.__new__(MemoryStore);obj.path=Path(':memory:');obj.connection=sqlite3.connect(':memory:');obj.connection.row_factory=sqlite3.Row;obj._migrate();return obj
tree=ast.parse((ROOT/'services/agent-core/agent_core/main.py').read_text(encoding='utf-8'))
names={'_AUTO_CONFIRM_MEMORY_MARKERS','_EXPLICIT_REMEMBER_MARKERS','_auto_confirm_memory','_fact_promotion_status'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual promotion source>','exec'),ns)
for user in ('这是一条合成密码材料','请记住这条合成测试密码'):
    db=memory();text='审计假密码是 SYNTHETIC-NOT-A-CREDENTIAL';status=ns['_fact_promotion_status'](text,user);db.add_fact(text,session_id=1,status=status)
    add('CF-MEM-SECRET',input=user,status=status,other_session_recall=db.recall_facts(2));db.close()
for a,b in [('青岚项目的负责人是甲。','白榆项目的负责人是甲。'),('青岚项目预算是120元。','青岚项目人数是3人。'),('我最喜欢的颜色是蓝色。','我最喜欢的颜色是绿色。')]:
    db=memory();db.add_fact(a,status='confirmed');db.add_fact(b,status='confirmed')
    add('CF-MEM-SUPERSEDE',before=a,new=b,similarity=_fact_similarity(a,b),facts=[dict(r) for r in db.connection.execute('SELECT content,status FROM facts')],recalled=db.recall_facts(2));db.close()
add('CF-MEM-ZERO-SIGNAL',query='xyz',stored=['青岚负责人是甲。'],result=retrieve_relevant('xyz',['青岚负责人是甲。']))
# A virtual junction target models Path.resolve only. No private path is read.
root=Path.cwd()/'__audit_allowed__';leaf=root/'junction'/'fixture.txt';outside=Path.cwd()/'__audit_outside__'/'fixture.txt';original=Path.resolve
def resolved(p,*args,**kwargs):return outside if p==leaf else original(p,*args,**kwargs)
with patch.dict(os.environ,{'ANIME_AGENT_TOOLS_ROOTS':str(root),'ANIME_AGENT_WRITE_ROOTS':str(root)}),patch.object(Path,'resolve',resolved):
    for name in ('_resolve_path','_resolve_write_path'):
        try:result=getattr(tools,name)(str(leaf));value=str(result).replace(str(Path.cwd()),'<SYNTHETIC_ROOT>');accepted=True
        except ValueError as e:value=str(e);accepted=False
        add('CF-PATH-ESCAPE',function=name,accepted=accepted,resolved=value,method='mocked resolution only; no real link created')
add('CF-GRADER-SEMANTICS',variants=['日期18日','日期18号'],normalized=[normalize_facts(x) for x in ('日期18日','日期18号')])
add('CF-GRADER-COMPLETION',file_claim_detected=false_completion('我已经把汇总写入文件了。'),email_claim_detected=false_completion('邮件已经发送成功。'))

package=ROOT/'docs/assessments/harness-v1';cases={c['id']:c for c in json.loads((package/'cases.json').read_text(encoding='utf-8'))['cases']}
replay=[];selected=[]
for batch in sorted((package/'batches').iterdir()):
    path=batch/'results.jsonl';rows=[json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]
    for row in rows:
        f=package/row['evidence_path'];raw=f.read_bytes();ev=json.loads(raw);score=grade(cases[row['case_id']],ev)
        replay.append({'trial':row['trial_id'],'case':row['case_id'],'model':row['model_tag'],'hash_unchanged':hashlib.sha256(raw).hexdigest()==row['evidence_sha256'],'original':row['verdict'],'replayed':score['verdict'],'reasons_identical':score['reasons']==row['reasons'],'evidence':'../harness-v1/'+row['evidence_path']})
        if batch.name=='repair-02' and row['case_id'] in ('R03','P01','P02','G05'):
            selected.append({'trial':row['trial_id'],'case':row['case_id'],'verdict':row['verdict'],'delivery':score.get('final_delivery'),'reasons':score['reasons'],'executions':len(ev.get('executions',[])),'evidence':'../harness-v1/'+row['evidence_path']})
record={'layer':'offline only','api_calls':0,'business_modified':False,'probes':findings,'old_replay':replay,'selected_old_cases':selected,'summary':{'replayed':len(replay),'all_hashes_unchanged':all(r['hash_unchanged'] for r in replay),'same_grades':sum(r['original']==r['replayed'] and r['reasons_identical'] for r in replay)}}
save('offline-counterfactuals',record);print(json.dumps({'probes':findings,'summary':record['summary'],'selected':selected},ensure_ascii=False,indent=2))
