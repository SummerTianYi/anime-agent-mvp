"""Codex: source-only route/method inventory, no runtime imports or requests."""
import ast, json, re
from pathlib import Path
from probe import ROOT, save

core=ROOT/'services/agent-core/agent_core'
tree=ast.parse((core/'main.py').read_text(encoding='utf-8'))
routes=[]; inputs=set()
for n in ast.walk(tree):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
        for d in n.decorator_list:
            if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=='app':
                routes.append({'kind':d.func.attr,'name':ast.literal_eval(d.args[0]) if d.args else None,'handler':n.name,'line':n.lineno})
    if isinstance(n,ast.Compare) and isinstance(n.left,ast.Name) and n.left.id=='event_type':
        for c in n.comparators:
            try:
                v=ast.literal_eval(c)
                inputs.update([v] if isinstance(v,str) else v)
            except (ValueError,TypeError):pass
schema=json.loads((ROOT/'docs/assessments/root-cause-audit/evidence/mcp-schema.json').read_text(encoding='utf-8'))
methods=[]
for server in schema['servers']:
    for tool in server['tools']:
        for arg,p in tool.get('inputSchema',{}).get('properties',{}).items():
            if 'enum' in p:
                methods.append({'tool':'mcp__'+server['server']+'__'+tool['name'],'argument':arg,'values':p['enum'],'verification':'schema only; individual operations NOT executed'})
gd=ROOT/'apps/avatar-runtime'
ui={p.name:re.findall(r'^func ([^(]+)',p.read_text(encoding='utf-8'),re.M) for p in (gd/'interaction_ui.gd',gd/'runtime.gd')}
out={'layer':'static actual source inventory; not functionality acceptance','source':'acc7bd4227c8e99a4adb7ed7266a8e1d06105ebd','routes':routes,'websocket_input_types':sorted(inputs),'mcp_enum_methods':methods,'godot_handlers':ui,'api_calls':0}
save('surface-inventory',out)
print(json.dumps({'routes':routes,'ws_inputs':sorted(inputs),'method_variants':sum(len(x['values']) for x in methods),'ui_handlers':{k:len(v) for k,v in ui.items()}},ensure_ascii=False))
