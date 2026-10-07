"""Independent read-only connector contrast on registered R2 objects.

Starts its own MCP children, never Core. Private raw receipts require manual
review before publication. Calls are fixed here, not arbitrary user commands.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--production', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--server', choices=['gmail', 'drive'])
a = p.parse_args()
a.production = a.production.resolve()
if a.output.exists():
    raise SystemExit('Refusing to replace existing evidence')
sys.path.insert(0, str(a.production / 'services/agent-core'))
sys.path.append(str(a.production.parent / 'tianyi-tts/venv/Lib/site-packages'))
import psutil
from agent_core.mcp_host import McpServer, _split_command, _resolve_command

for line in (a.production / '.env').read_text(encoding='utf-8-sig').splitlines():
    key, sep, value = line.partition('=')
    if sep and key and not key.startswith('#'):
        os.environ[key.strip()] = value.strip().strip('"').strip("'")
os.environ['NPM_CONFIG_OFFLINE'] = 'true'

CASES = {
    'gmail': [
        ('tools/call', {'name': 'search_emails', 'arguments': {'query': 'subject:"[R2-20261007] Fixture inbox 01"', 'maxResults': 3}}),
        ('tools/call', {'name': 'read_email', 'arguments': {'messageId': '1a1170bf8fa1edf8'}}),
        ('tools/call', {'name': 'search_emails', 'arguments': {'query': 'subject:R2-20261007-NONEXISTENT-91E7', 'maxResults': 1}}),
        ('tools/call', {'name': 'read_email', 'arguments': {'messageId': 'r2-invalid-message-91e7'}}),
    ],
    'drive': [
        ('tools/call', {'name': 'search', 'arguments': {'query': 'R2-TIANYI-Drive-evidence'}}),
        ('tools/call', {'name': 'search', 'arguments': {'query': 'R2-20261007-NONEXISTENT-91E7'}}),
        ('resources/read', {'uri': 'gdrive:///1A8qruMefQjK-q1Bca1zSnCzo2KhYSETH'}),
    ],
}

async def main():
    rows = []
    for entry in os.environ.get('ANIME_AGENT_MCP_SERVERS', '').split(os.pathsep):
        name, sep, command = entry.partition('=')
        if not sep or name not in CASES or (a.server and name != a.server):
            continue
        server = McpServer(name, _resolve_command(_split_command(command)))
        original_roundtrip = server._roundtrip
        startup_wire = []
        class ObservedStream:
            def __init__(self, wrapped):
                self.wrapped = wrapped
            async def readline(self):
                raw = await self.wrapped.readline()
                if len(startup_wire) < 20:
                    startup_wire.append({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                                         'prefix': raw[:2000].decode('utf-8', errors='replace')})
                return raw
            def __getattr__(self, attr):
                return getattr(self.wrapped, attr)
        async def observed_roundtrip(*args, **kwargs):
            if not isinstance(server.process.stdout, ObservedStream):
                server.process.stdout = ObservedStream(server.process.stdout)
            return await original_roundtrip(*args, **kwargs)
        server._roundtrip = observed_roundtrip
        try:
            await asyncio.wait_for(server.start(), 30)
            rows.append({'server': name, 'startup_wire': startup_wire.copy()})
            server._roundtrip = original_roundtrip
            for method, params in CASES[name]:
                request = {'jsonrpc': '2.0', 'id': server.next_id, 'method': method, 'params': params}
                server.next_id += 1
                try:
                    receipt = await server._roundtrip(request, timeout=30)
                    row = {'server': name, 'request': request, 'raw': receipt}
                    rows.append(row)
                    if method == 'tools/call':
                        # Reuse the same captured receipt in the deployed adapter;
                        # no second remote call and no fabricated service success.
                        original = server._roundtrip
                        async def replay(*args, **kwargs):
                            return receipt
                        server._roundtrip = replay
                        try:
                            row['adapted_same_receipt'] = await server.call(params['name'], params['arguments'])
                        except Exception as exc:
                            row['adaptation_error'] = {'type': type(exc).__name__, 'message': str(exc)[:300]}
                        finally:
                            server._roundtrip = original
                except Exception as exc:
                    rows.append({'server': name, 'request': request, 'error_type': type(exc).__name__, 'message': str(exc)[:300]})
        except Exception as exc:
            rows.append({'server': name, 'startup_error': type(exc).__name__, 'message': str(exc)[:300], 'startup_wire': startup_wire})
        finally:
            children = []
            cleanup_errors = []
            if server.process:
                try:
                    children = [(c.pid, c.create_time()) for c in psutil.Process(server.process.pid).children(recursive=True)]
                except psutil.Error:
                    pass
                await server.stop()
                try:
                    await asyncio.wait_for(server.process.wait(), 5)
                except asyncio.TimeoutError:
                    rows.append({'server': name, 'cleanup_root_still_running': server.process.pid})
                owned = []
                for pid, created in reversed(children):
                    try:
                        child = psutil.Process(pid)
                        if child.create_time() == created:
                            child.terminate()
                            owned.append(child)
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.Error as exc:
                        cleanup_errors.append({'pid': pid, 'type': type(exc).__name__})
                _, alive = psutil.wait_procs(owned, timeout=5)
                rows.append({'server': name, 'cleanup': {'root_returncode': server.process.returncode,
                             'remaining_owned_children': [c.pid for c in alive], 'cleanup_errors': cleanup_errors}})
    report = {'actor': 'Codex independent verification, NOT Tianyi execution',
              'external_mutations': [], 'private': True,
              'adapter_sha256': hashlib.sha256((a.production / 'services/agent-core/agent_core/mcp_host.py').read_bytes()).hexdigest(),
              'rows': rows}
    with a.output.open('x', encoding='utf-8') as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
    print(json.dumps({'calls_attempted': sum('request' in r for r in rows),
                      'transport_errors': sum('error_type' in r for r in rows),
                      'adapter_errors': sum('adaptation_error' in r for r in rows),
                      'startup_errors': sum('startup_error' in r for r in rows),
                      'output': str(a.output)}))

asyncio.run(main())
