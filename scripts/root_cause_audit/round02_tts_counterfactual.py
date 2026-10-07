"""Replay the exact failing print in memory; never load GPU models or call TTS."""
import argparse
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import urllib.error

p = argparse.ArgumentParser()
p.add_argument('--production', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
production = a.production.resolve()
tts = production.parent / 'tianyi-tts'
source = tts / 'GPT-SoVITS/GPT_SoVITS/inference_webui.py'
source_bytes = source.read_bytes()
tree = ast.parse(source_bytes)
stmt = next(n for n in ast.walk(tree) if isinstance(n, ast.Expr) and
            isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and
            n.value.func.id == 'print' and '实际输入的目标文本:' in ast.unparse(n))
code = compile(ast.Module(body=[stmt], type_ignores=[]), str(source), 'exec')
cases = []
for text, encoding in [('已经读取完毕 ✅', 'gbk'), ('已经读取完毕', 'gbk'),
                       ('已经读取完毕 ✅', 'utf-8')]:
    raw = io.BytesIO()
    with io.TextIOWrapper(raw, encoding=encoding, errors='surrogateescape') as stream:
        try:
            with contextlib.redirect_stdout(stream):
                exec(code, {'text': text, 'i18n': lambda value: value})
            stream.flush()
            outcome = {'status': 'printed', 'bytes': len(raw.getvalue())}
        except UnicodeEncodeError as exc:
            outcome = {'status': type(exc).__name__, 'start': exc.start, 'end': exc.end, 'reason': exc.reason}
    cases.append({'text': text, 'encoding': encoding, 'errors': 'surrogateescape', **outcome})
speech_path = production / 'services/agent-core/agent_core/speech.py'
spec = importlib.util.spec_from_file_location('r2_isolated_speech', speech_path)
speech = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = speech
spec.loader.exec_module(speech)
retry_cases = []
for status in [400, 503]:
    def fake_post(*args, **kwargs):
        raise urllib.error.HTTPError('http://synthetic.invalid', status, 'synthetic', {}, None)
    speech._post_json = fake_post
    try:
        speech.SpeechClient('http://synthetic.invalid').synthesize('合成文本')
    except speech.SpeechUnavailable as exc:
        retry_cases.append({'http_status': status, 'retryable': exc.retryable})
report = {'layer': 'isolated deployed source print and HTTP classification, no network/GPU/Core process',
          'live_request_id': 'avatar-chat-1913607', 'source_line': stmt.lineno,
          'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
          'speech_sha256': hashlib.sha256(speech_path.read_bytes()).hexdigest(),
          'print_cases': cases, 'http_classification': retry_cases,
          'limits': 'UTF-8 print success is not evidence that full synthesis of arbitrary emoji succeeds.'}
with a.output.open('x', encoding='utf-8') as file:
    json.dump(report, file, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=True))
