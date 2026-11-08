"""Real WS lifecycle and worker recovery with synthetic devices only."""
import asyncio
from contextlib import contextmanager
import tempfile
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import numpy as np
from fastapi.testclient import TestClient
from agent_core import main as core
from agent_core import wake_word as ww
from agent_core.stt_input import CaptureState
from agent_core.storage import MemoryStore
from agent_core.voice import VoiceError
from agent_core.wake_word import WakeWordListener


class Listener:
    paused = False
    resumes = 0
    def pause(self): self.paused = True
    def resume(self): self.paused = False; self.resumes += 1


class Recorder:
    recording = False
    def __init__(self, failure=None): self.failure = failure
    def start(self):
        if self.failure == 'start': raise VoiceError('synthetic open failure')
        self.recording = True
    def stop(self):
        self.recording = False
        if self.failure == 'stop': raise VoiceError('synthetic stop failure')
        return b'synthetic'
    def cancel(self): self.recording = False


@contextmanager
def runtime(failure=None):
    with tempfile.TemporaryDirectory() as directory:
        memory = MemoryStore(data_dir=Path(directory))
        listener, recorder = Listener(), Recorder(failure)
        try:
            with patch.object(core, 'memory', memory), patch.object(core, 'voice_capture', CaptureState()), \
                    patch.object(core, 'voice_recorder', recorder), patch.object(core, 'wake_listener', None), \
                    patch.object(core, '_wake_busy', False), patch.object(core, 'TTS_ENABLED', False), \
                    patch.object(core, 'VOICE_INPUT_MODE', 'manual'), \
                    patch.object(core, 'transcribe_wav', lambda _: '测试'), \
                    patch.object(core, 'simplify_transcript', lambda text: text):
                with TestClient(core.app) as client:
                    with patch.object(core, 'VOICE_INPUT_MODE', 'wake'), patch.object(core, 'wake_listener', listener):
                        yield client, listener, recorder
        finally:
            memory.close()


def barrier(ws):
    ws.send_json({'type': 'ping'})
    while ws.receive_json()['type'] != 'pong': pass


class WakeCaptureRecoveryTests(unittest.TestCase):
    def test_failure_cancel_switch_disconnect_rearm(self):
        for scenario in ('start', 'stop', 'cancel', 'session.new', 'session.delete', 'chat.history.request', 'disconnect'):
            with self.subTest(scenario=scenario), runtime(scenario) as (client, listener, recorder):
                delete_session = core.memory.create_session() if scenario == 'session.delete' else None
                with client.websocket_connect('/ws') as ws:
                    ws.send_json({'type': 'voice.start', 'captureId': 'first'})
                    if scenario == 'stop': ws.send_json({'type': 'voice.stop', 'captureId': 'first'})
                    elif scenario == 'cancel': ws.send_json({'type': 'voice.cancel'})
                    elif scenario in ('session.new', 'chat.history.request'): ws.send_json({'type': scenario})
                    elif scenario == 'session.delete':
                        ws.send_json({'type': scenario, 'conversationId': delete_session['id']})
                    barrier(ws)
                self.assertFalse(listener.paused)
                self.assertFalse(recorder.recording)
                self.assertGreaterEqual(listener.resumes, 1)

    def test_normal_transcription_rearms(self):
        with runtime() as (client, listener, recorder), client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'voice.start', 'captureId': 'normal'})
            barrier(ws)
            self.assertTrue(listener.paused)
            ws.send_json({'type': 'voice.stop', 'captureId': 'normal'})
            barrier(ws)
            deadline = time.monotonic() + 2
            while listener.paused and time.monotonic() < deadline: time.sleep(.005)
            self.assertFalse(listener.paused)
            self.assertEqual(listener.resumes, 1)

    def test_old_transcription_cannot_resume_new_capture(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        def transcribe(_):
            entered.set()
            release.wait(3)
            finished.set()
            return '迟到'
        with runtime() as (client, listener, recorder), patch.object(core, 'transcribe_wav', transcribe):
            try:
                with client.websocket_connect('/ws') as ws:
                    ws.send_json({'type': 'voice.start', 'captureId': 'old'})
                    ws.send_json({'type': 'voice.stop', 'captureId': 'old'})
                    barrier(ws)
                    self.assertTrue(entered.wait(2))
                    ws.send_json({'type': 'voice.start', 'captureId': 'new'})
                    barrier(ws)
                    release.set()
                    self.assertTrue(finished.wait(2))
                    time.sleep(.03)
                    barrier(ws)
                    self.assertTrue(listener.paused)
                    self.assertTrue(recorder.recording)
                    self.assertEqual(listener.resumes, 0)
            finally: release.set()

    def test_manual_mode_never_rearms(self):
        with runtime('start') as (client, listener, recorder), patch.object(core, 'VOICE_INPUT_MODE', 'manual'):
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'type': 'voice.start', 'captureId': 'manual'})
                ws.send_json({'type': 'voice.cancel'})
                barrier(ws)
            self.assertEqual(listener.resumes, 0)

    def test_unrelated_socket_disconnect_does_not_release_active_capture(self):
        with runtime() as (client, listener, recorder), client.websocket_connect('/ws') as owner:
            owner.send_json({'type': 'voice.start', 'captureId': 'owned'})
            barrier(owner)
            with client.websocket_connect('/ws') as other: barrier(other)
            self.assertTrue(listener.paused)
            self.assertTrue(recorder.recording)
            self.assertEqual(listener.resumes, 0)

    def test_cancel_waits_for_inflight_wake_capture_to_release(self):
        with runtime() as (_, listener, recorder), patch.object(core, '_wake_busy', True):
            listener.pause()
            core.invalidate_voice()
            self.assertTrue(listener.paused)
            self.assertEqual(listener.resumes, 0)

    def test_pause_timeout_does_not_open_manual_recorder(self):
        with runtime() as (client, listener, recorder), patch.object(listener, 'pause', side_effect=VoiceError('synthetic timeout')), \
                patch.object(recorder, 'start') as start, client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'voice.start', 'captureId': 'timeout'})
            barrier(ws)
            start.assert_not_called()
            self.assertEqual(core.voice_capture.phase, 'idle')

    def test_old_or_foreign_cancel_cannot_release_new_recording(self):
        with runtime() as (client, listener, recorder), client.websocket_connect('/ws') as owner:
            owner.send_json({'type': 'voice.start', 'captureId': 'new'})
            barrier(owner)
            owner.send_json({'type': 'voice.cancel', 'captureId': 'old'})
            barrier(owner)
            with client.websocket_connect('/ws') as other:
                other.send_json({'type': 'voice.cancel', 'captureId': 'new'})
                barrier(other)
            self.assertTrue(recorder.recording)
            self.assertTrue(listener.paused)
            self.assertEqual(listener.resumes, 0)

    def test_wake_during_manual_open_is_ignored(self):
        with runtime() as (_, listener, recorder), patch.object(listener, 'pause') as pause, \
                patch.object(core, '_agent_state', 'idle'), patch.dict(core._voice_refractory, {'last_voice_stop': 0}):
            core.voice_capture.phase = 'recording'
            asyncio.run(core.handle_wake_word(np.ones(1600, dtype=np.float32)))
            pause.assert_not_called()
            self.assertFalse(core._wake_busy)

    def test_pause_timeout_is_controlled_and_releases_wake_ownership(self):
        with runtime() as (_, listener, recorder), patch.object(listener, 'pause', side_effect=VoiceError('synthetic timeout')), \
                patch.object(core, '_agent_state', 'idle'), patch.dict(core._voice_refractory, {'last_voice_stop': 0}):
            asyncio.run(core.handle_wake_word(np.ones(1600, dtype=np.float32)))
            self.assertFalse(core._wake_busy)

    def test_model_load_failure_does_not_fail_core_startup(self):
        class FailedStart:
            def __init__(self, **kwargs): pass
            def start(self): raise VoiceError('synthetic missing model')
        with runtime() as (_, listener, recorder), patch.object(core, 'WakeWordListener', FailedStart), \
                patch.object(core, 'wake_listener', None), patch.dict(core.os.environ, {'ANIME_AGENT_WAKE_WORD': '1'}):
            asyncio.run(core.start_wake_word_listener())
            self.assertIsNone(core.wake_listener)


class Spotter:
    fail_decode = False
    def create_stream(self): return SimpleNamespace(accept_waveform=lambda *args: None)
    def is_ready(self, stream):
        if self.fail_decode:
            self.fail_decode = False
            raise RuntimeError('synthetic decode failure')
        return False
    def get_result(self, stream): return '天依'
    def reset_stream(self, stream): pass


class WakeAcknowledgementTests(unittest.TestCase):
    def run_wake(self, command, *, cancel_ack=False, cancel_transcript=None):
        order, events = [], []
        async def speak(text, request_id):
            order.append(('ack', text))
            if cancel_ack: core.cancel_utterance_capture()
            return not cancel_ack
        async def send(roles, item):
            events.append(item)
            if item['type'] == 'wake.triggered': order.append(('ready', None))
        def capture(token, *, on_ready):
            order.append(('mic-open', None))
            self.assertTrue(on_ready())
            return None if command is None else b'synthetic-command'
        transcripts = ['嗨天依'] + ([] if command is None else [command])
        def transcribe(_audio):
            result = transcripts.pop(0)
            if result == cancel_transcript:
                core.cancel_utterance_capture()
            if isinstance(result, Exception):
                raise result
            return result
        with runtime() as (_, listener, recorder), patch.object(core, 'TTS_ENABLED', True), \
                patch.object(core, '_agent_state', 'idle'), patch.dict(core._voice_refractory, {'last_voice_stop': 0}), \
                patch.object(core.hub, 'role_count', return_value=1), patch.object(core.hub, 'send_roles', send), \
                patch.object(core, '_speak_reply', speak), patch.object(core, 'transcribe_wav', side_effect=transcribe), \
                patch.object(core, 'capture_utterance', side_effect=capture) as captured, \
                patch.object(core.memory, 'create_session', wraps=core.memory.create_session) as created, \
                patch.object(core, 'handle_chat', new_callable=AsyncMock) as chat:
            asyncio.run(core.handle_wake_word(np.ones(1600, dtype=np.float32)))
            self.assertFalse(listener.paused)
            self.assertFalse(core._wake_busy)
            return order, events, captured.call_count, chat.call_count, created.call_count

    def test_wake_only_speaks_without_creating_empty_chat(self):
        order, events, captures, chats, sessions = self.run_wake(None)
        self.assertEqual(order, [('ack', '我在，请讲。'), ('mic-open', None), ('ready', None)])
        self.assertEqual((captures, chats, sessions), (1, 0, 0))

    def test_command_dispatched_after_ack_and_real_capture_ready(self):
        order, events, captures, chats, sessions = self.run_wake('你好')
        self.assertEqual([item[0] for item in order], ['ack', 'mic-open', 'ready'])
        self.assertEqual((captures, chats, sessions), (1, 1, 1))

    def test_transcription_failure_is_visible_and_does_not_dispatch(self):
        order, events, captures, chats, sessions = self.run_wake(VoiceError('没有识别到清晰语音'))
        self.assertTrue(any(item['type'] == 'core.error' and '未能转写' in item['message'] for item in events))
        self.assertEqual((chats, sessions), (0, 0))

    def test_cancelled_ack_does_not_open_command_microphone(self):
        order, events, captures, chats, sessions = self.run_wake(None, cancel_ack=True)
        self.assertEqual((captures, chats, sessions), (0, 0, 0))
        self.assertFalse(any(item['type'] == 'wake.triggered' for item in events))

    def test_cancel_during_wake_confirmation_does_not_speak_or_capture(self):
        order, events, captures, chats, sessions = self.run_wake('你好', cancel_transcript='嗨天依')
        self.assertEqual(order, [])
        self.assertEqual((captures, chats, sessions), (0, 0, 0))

    def test_cancel_during_command_transcription_does_not_dispatch(self):
        order, events, captures, chats, sessions = self.run_wake('你好', cancel_transcript='你好')
        self.assertEqual((captures, chats, sessions), (1, 0, 0))


class Mic:
    def start(self): pass
    def read(self, count):
        time.sleep(.005)
        return np.ones(count, dtype=np.float32) * .01, False
    def stop(self): pass
    def close(self): pass


class CommandCaptureTests(unittest.TestCase):
    def run_capture(self, *, ready=True, read_failure=False, stop_failure=False):
        order = []
        class CommandMic:
            def start(self): order.append('start')
            def read(self, count):
                order.append('read')
                if read_failure: raise RuntimeError('synthetic device failure')
                return np.full(count, .01, dtype=np.float32), False
            def stop(self):
                order.append('stop')
                if stop_failure: raise RuntimeError('synthetic stop failure')
            def close(self): order.append('close')
        def on_ready():
            order.append('ready')
            return ready
        with patch.object(ww, '_import_audio_dependencies', return_value=(
                np, SimpleNamespace(InputStream=lambda **kwargs: CommandMic()))):
            if read_failure:
                with self.assertRaisesRegex(VoiceError, '麦克风录音中断'):
                    ww.capture_utterance(max_seconds=.1, min_speech_seconds=.1, on_ready=on_ready)
                audio = None
            else:
                audio = ww.capture_utterance(max_seconds=.1, min_speech_seconds=.1, on_ready=on_ready)
        return order, audio

    def test_ready_after_mic_start_and_short_command_preserved(self):
        order, audio = self.run_capture()
        self.assertEqual(order, ['start', 'ready', 'read', 'stop', 'close'])
        self.assertTrue(audio.startswith(b'RIFF'))

    def test_cancel_at_ready_closes_without_reading(self):
        order, audio = self.run_capture(ready=False)
        self.assertIsNone(audio)
        self.assertEqual(order, ['start', 'ready', 'stop', 'close'])

    def test_read_failure_is_controlled_and_stop_failure_still_closes(self):
        order, audio = self.run_capture(read_failure=True, stop_failure=True)
        self.assertEqual(order[-2:], ['stop', 'close'])


class WakeWorkerRecoveryTests(unittest.TestCase):
    def test_pause_closes_on_reader_thread_after_read_finishes(self):
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()
        threads = {}
        class BlockingMic(Mic):
            def read(self, count):
                threads['read'] = threading.get_ident()
                entered.set()
                release.wait(2)
                return super().read(count)
            def close(self):
                threads['close'] = threading.get_ident()
                closed.set()
        listener = WakeWordListener(lambda _: None)
        with patch('agent_core.wake_word.build_keyword_spotter', return_value=Spotter()), \
                patch('agent_core.wake_word._import_audio_dependencies', return_value=(np, SimpleNamespace(InputStream=lambda **kwargs: BlockingMic()))):
            listener.start()
            pausing = threading.Thread(target=listener.pause)
            try:
                self.assertTrue(entered.wait(2))
                pausing.start()
                self.assertFalse(closed.wait(.03))
                release.set()
                pausing.join(2)
                self.assertFalse(pausing.is_alive())
                self.assertTrue(closed.is_set())
                self.assertEqual(threads['read'], threads['close'])
            finally:
                release.set()
                listener.stop()
                if pausing.ident: pausing.join(2)

    def test_decoder_failure_recovers_and_detects(self):
        detected = threading.Event()
        spotter = Spotter()
        spotter.fail_decode = True
        listener = WakeWordListener(lambda _: detected.set())
        with patch('agent_core.wake_word.build_keyword_spotter', return_value=spotter), \
                patch('agent_core.wake_word._import_audio_dependencies', return_value=(np, SimpleNamespace(InputStream=lambda **kwargs: Mic()))):
            listener.start()
            try:
                self.assertTrue(detected.wait(3))
                self.assertTrue(listener.running)
            finally: listener.stop()

    def test_microphone_failures_recover_and_detect(self):
        for fail_at in ('open', 'read'):
            with self.subTest(fail_at=fail_at):
                calls = []
                detected = threading.Event()
                class ReadFailure(Mic):
                    def read(self, count): raise RuntimeError('synthetic read failure')
                def factory(**kwargs):
                    calls.append(1)
                    if len(calls) == 1:
                        if fail_at == 'open': raise RuntimeError('synthetic open failure')
                        return ReadFailure()
                    return Mic()
                listener = WakeWordListener(lambda _: detected.set())
                with patch('agent_core.wake_word.build_keyword_spotter', return_value=Spotter()), \
                        patch('agent_core.wake_word._import_audio_dependencies', return_value=(np, SimpleNamespace(InputStream=factory))):
                    listener.start()
                    try:
                        self.assertTrue(detected.wait(3))
                        self.assertGreaterEqual(len(calls), 2)
                        self.assertEqual(listener.phase, 'listening')
                        self.assertIsNotNone(listener.read_age_seconds)
                    finally: listener.stop()

    def test_failed_stream_start_closes_allocated_device(self):
        mic = Mic()
        with patch.object(mic, 'start', side_effect=RuntimeError('synthetic')), patch.object(mic, 'close') as close:
            listener = WakeWordListener(lambda _: None)
            listener._sounddevice = SimpleNamespace(InputStream=lambda **kwargs: mic)
            with self.assertRaises(RuntimeError): listener._open_mic()
            close.assert_called_once()
