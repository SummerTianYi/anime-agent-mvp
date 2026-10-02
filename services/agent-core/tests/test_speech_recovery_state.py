"""Codex: voice recovery must not deadlock listening or emit stale state."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from agent_core import main as core


class SpeechRecoveryStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_waiting_final_reply_releases_thinking_state(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def speak(*args):
            entered.set()
            await release.wait()
            return SimpleNamespace(cancelled=True,has_audio=False)
        manager=SimpleNamespace(speak=speak,current=object())
        states=AsyncMock()
        with patch.object(core,'speech_manager',manager), patch.object(core,'broadcast_state',states):
            task=asyncio.create_task(core._speak_reply('测试','recovery-state-fixture'))
            await asyncio.wait_for(entered.wait(),.5)
            states.assert_awaited_once_with('idle','recovery-state-fixture')
            release.set()
            await task
            self.assertEqual(states.await_count,1,'cancelled generation overwrote state')

    async def test_idle_greeting_cannot_supersede_pending_user_reply(self):
        with patch.object(core,'speech_manager',SimpleNamespace(current=object())), patch.object(core,'_speak_reply',AsyncMock()) as speak:
            await core._proactive_idle(9999)
            speak.assert_not_awaited()
