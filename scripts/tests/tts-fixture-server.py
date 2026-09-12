"""Codex fault fixture: real HTTP handler, synthetic WAV, no GPU/provider/mic."""
import json
import os
from pathlib import Path
import sys
import threading
import time
import types
import wave
import math
import struct

root = Path(__file__).resolve().parents[1]
assert (root / '.tts-test-fixture').is_file()
control = root / 'control.json'

def settings():
    try: return json.loads(control.read_text())
    except (OSError, ValueError): return {}

class Checker:
    enabled=False; threshold=.9; takes=0; retries=0
    def __init__(self, *_args): pass
    def run(self, text, speed, fn, temperature):
        self.takes += 1
        return fn(text, speed, temperature)

sys.modules['voice_selfcheck'] = types.SimpleNamespace(VoiceSelfCheck=Checker)
import tts_implementation as impl
assert impl.WORK.resolve() == root
assert impl.SPOOL.resolve().is_relative_to(root), 'Synthetic tests must never prune the live audio spool'

def load(_config):
    time.sleep(float(settings().get('warm', 0)))
    def synth(text, speed, temperature):
        if settings().get('mode') == 'synth_error': raise RuntimeError('injected model failure')
        if settings().get('mode') == 'synth_hang':
            impl._lifecycle.busy_limit = .7
            while True: time.sleep(.1)
        time.sleep(float(settings().get('synth_delay', 0)))
        dst=root/'out'/'fixture.wav'; dst.parent.mkdir(exist_ok=True)
        with wave.open(str(dst),'wb') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(32000)
            wav.writeframes(b''.join(struct.pack('<h',int(2000*math.sin(i*.1))) for i in range(3200)))
        return {'ok':True,'audioPath':str(dst),'durationMs':100,'sampleRate':32000}
    return synth

original_get=impl.Handler.do_GET
def get(self):
    if settings().get('legacy_pid') == os.getpid():
        self._send_json({'ok':True,'device':'test-legacy'}); return
    if settings().get('mode') == 'health_hang':
        time.sleep(20)
    return original_get(self)
impl.Handler.do_GET=get
impl.load_models=load

def fault_loop():
    while True:
        if settings().get('mode') == 'crash': os._exit(23)
        time.sleep(.1)
threading.Thread(target=fault_loop,daemon=True).start()
impl.main()
