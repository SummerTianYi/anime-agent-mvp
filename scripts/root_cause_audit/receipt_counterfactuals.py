"""Codex: execute real MCP receipt/ledger/delivery code against synthetic replies."""
import ast, asyncio, json, re, sqlite3, sys
from pathlib import Path
from unittest.mock import AsyncMock
from probe import ROOT, save
sys.path.insert(0,str(ROOT/'services/agent-core'))
from agent_core.mcp_host import McpServer
from agent_core.actions import ActionLedger

tree=ast.parse((ROOT/'services/agent-core/agent_core/main.py').read_text(encoding='utf-8'))
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_receipt_delivery')
book=None
ns=dict(json=json,re=re,_actions=lambda:book)
exec(compile(ast.Module(body=[fn],type_ignores=[]),'receipt','exec'),ns)
rows=[]

async def run():
    global book
    for flag in ('omitted',False,True,'rpc-error'):
        for tool in ('search_emails','send_email'):
            db=sqlite3.connect(':memory:');book=ActionLedger(db)
            server=McpServer(name='synthetic',command=[])
            content={'content':[{'type':'text','text':'Error: invalid_grant'}]}
            if isinstance(flag,bool):content['isError']=flag
            wire={'error':{'code':-32603,'message':'invalid_grant'}} if flag=='rpc-error' else {'result':content}
            server._roundtrip=AsyncMock(return_value=wire)
            async def execute(name,args):
                result=await server.call(tool,args)
                return {'ok':result.get('ok',False),'output':result.get('text',''),**({'error':result['error']} if 'error' in result else {})}
            item=book.propose(1,'t','proposal','mcp__gmail__'+tool,{'synthetic':True})
            receipt=await book.execute(1,book.ticket(item),'confirm',lambda *_:True,execute)
            delivery=ns['_receipt_delivery'](1,{'id':'t'},'我先执行查询。')
            rows.append(dict(flag=flag,tool=tool,wire=wire,receipt=receipt,delivery=delivery))
            assert item['status']==('failed' if flag is True or flag=='rpc-error' else 'succeeded')
            db.close()
    # A text mentioning Error inside valid content is a success control. No global keyword policy is inferred.
    server=McpServer(name='synthetic',command=[])
    server._roundtrip=AsyncMock(return_value={'result':{'content':[{'type':'text','text':'Document title: Error handling guide'}]}})
    control=await server.call('read',{})
    assert control['ok'] is True
    return control

control=asyncio.run(run())
record={'layer':'offline synthetic; no remote email or connector process','api_calls':0,'business_modified':False,'cases':rows,'valid_error_word_control':control}
save('receipt-counterfactuals',record)
print(json.dumps({'cases':len(rows),'statuses':[r['receipt']['outcome'] for r in rows],'control_ok':control['ok']},ensure_ascii=False))
