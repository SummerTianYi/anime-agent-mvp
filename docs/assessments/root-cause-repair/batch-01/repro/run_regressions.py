"""Run batch mechanism tests against an explicitly chosen source tree.

Writes only synthetic temporary stores. Refuses editable-install source drift.
No desktop or real model/service acceptance is claimed by this runner.
"""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--private-log',type=Path,help='Optional local-only diagnostic output; never publish without review')
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[5]
    package=(args.source_root/'services'/'agent-core').resolve()
    sys.path.insert(0,str(package))
    sys.path.insert(0,str(repo/'services'/'agent-core'/'tests'))
    with tempfile.TemporaryDirectory(prefix='tianyi-b01-runner-') as directory:
        os.environ.update(ANIME_AGENT_DATA_DIR=directory,
            ANIME_AGENT_CONFIG_PATH=str(Path(directory)/'absent.env'),
            ANIME_AGENT_TTS='0',ANIME_AGENT_WAKE_WORD='0',ANIME_AGENT_MCP_SERVERS='',LLM_PROVIDER='mock')
        from agent_core import main as core
        actual=Path(core.__file__).resolve()
        if package not in actual.parents:
            raise RuntimeError('Wrong imported source; refusing false candidate evidence')
        tests=unittest.defaultTestLoader.discover(str(repo/'services'/'agent-core'/'tests'),pattern='test_repair_batch01.py')
        output=io.StringIO()
        try:
            with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
                result=unittest.TextTestRunner(stream=output,verbosity=0).run(tests)
        finally:
            core.memory.close()
        record={'kind':'isolated mechanism regression; not desktop acceptance',
                'source_module_sha256':__import__('hashlib').sha256(actual.read_bytes()).hexdigest(),
                'tests_run':result.testsRun,'failures':[case.id() for case,_ in result.failures],
                'errors':[case.id() for case,_ in result.errors],
                'skipped':[(case.id(),reason) for case,reason in result.skipped],
                'success':result.wasSuccessful(),'real_model_calls':0,'desktop_actions':0}
        args.output.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        if args.private_log:
            args.private_log.write_text(output.getvalue(),encoding='utf-8')
        print(json.dumps(record,ensure_ascii=False))
        # The concise JSON records failures without exporting model prompts,
        # filesystem names from temporary fixtures, or synthesized stack dumps.
        return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    raise SystemExit(main())
