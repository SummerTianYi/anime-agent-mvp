"""Codex: reproduce the observed scope mismatch in isolated synthetic memory."""
import ast,sqlite3,sys
from pathlib import Path
from probe import ROOT,save
sys.path.insert(0,str(ROOT/'services/agent-core'))
from agent_core.storage import MemoryStore
tree=ast.parse((ROOT/'services/agent-core/agent_core/main.py').read_text(encoding='utf-8'))
names={'_AUTO_CONFIRM_MEMORY_MARKERS','_EXPLICIT_REMEMBER_MARKERS','_auto_confirm_memory','_fact_promotion_status'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual promotion functions','exec'),ns)
rows=[]
for wording in ('请保存更正','请记住更正'):
    db=MemoryStore.__new__(MemoryStore);db.path=Path(':memory:');db.connection=sqlite3.connect(':memory:');db.connection.row_factory=sqlite3.Row;db._migrate()
    for user,candidate in [('请记住','审计青岚项目负责人林岚，预算120元，合成测试数据'),(wording,'审计青岚项目负责人林岚，预算180元，合成测试数据')]:
        status=ns['_fact_promotion_status'](candidate,user)
        db.add_fact(candidate,session_id=1,scope='global' if status=='confirmed' else 'session',status=status)
    facts=[dict(r) for r in db.connection.execute('SELECT content,scope,status FROM facts')]
    recalled=db.recall_facts(2)
    rows.append({'wording':wording,'facts':facts,'next_session_recall':recalled})
    assert ('120' in str(recalled)) == (wording=='请保存更正')
    assert ('180' in str(recalled)) == (wording=='请记住更正')
    db.close()
save('memory-correction-counterfactual',{'layer':'isolated causal contrast, no live data modification','api_calls':0,'rows':rows})
print('MEMORY_SCOPE_COUNTERFACTUAL_PASS')
