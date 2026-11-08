import tempfile
import unittest
from pathlib import Path

from agent_core.conversation_context import model_history
from agent_core.storage import MemoryStore


class ConversationContextTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = MemoryStore(Path(tmp.name))
        self.addCleanup(self.store.close)
        self.sid = self.store.create_session()["id"]

    def test_bound_history_keeps_real_chat_and_omits_receipts(self):
        for role,text,rid in (
            ("user","今天不想听建议。","one"),("assistant","嗯。","one"),
            ("user","请读取文件旧.txt","two"),("task_receipt","synthetic old file body","two"),
            ("user","我的花开了。顺便读取文件花.txt。","three"),("assistant","开花了呀。","three"),
            ("task_receipt","synthetic other result","three"),("memory_receipt","少量记忆待确认","three"),
            ("user","我想换个话题","now"),("user","下一轮不应出现","future")):
            self.store.add_message(role,text,rid,self.sid)
        self.store.add_message("user","别的会话", "else",self.store.create_session()["id"])
        history=model_history(self.store,self.sid,"now","我想换个话题",companion=True,limit=20)
        self.assertEqual([x["content"] for x in history],["今天不想听建议。","嗯。","我的花开了。","开花了呀。","我想换个话题"])
        history=model_history(self.store,self.sid,"now","我想换个话题",companion=False,limit=20)
        self.assertEqual(history[-1]["content"],"我想换个话题")
        self.assertTrue(all(x["role"] in ("user","assistant") for x in history))
        self.assertNotIn("下一轮不应出现",str(history))
