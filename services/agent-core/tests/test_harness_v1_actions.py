import asyncio
import sqlite3
import unittest
from agent_core.actions import ActionLedger, decision


class ActionsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.book = ActionLedger(self.db)
        self.calls = []

    async def execute(self, tool, args):
        self.calls.append((tool,args))
        return {"ok":True,"path":args.get("path"),"content":args.get("content")}

    def propose(self, content="a", task="task"):
        return self.book.propose(1,task,"origin","write_file",{"path":"x","content":content})

    async def test_negative_and_quoted_affirmative_never_approve(self):
        for text in ("不同意，先不要执行。","不同意发送请不要执行","不要取消，改为新参数","他说确认","确认但改成B","不确认","yes cancel"):
            self.assertNotEqual(decision(text),"approve",text)
        self.assertEqual(decision("确认"),"approve")

    async def test_revision_is_not_reusable_and_multiple_actions_survive(self):
        a,b = self.propose("a"),self.propose("b")
        self.assertEqual(len(self.book.pending(1)),2)
        self.assertNotEqual(a["args_hash"], b["args_hash"])
        stale = self.book.ticket(a) | {"revision":b["revision"]}
        result = await self.book.execute(1,stale,"confirm",lambda *_:True,self.execute)
        self.assertFalse(result["ok"]); self.assertFalse(self.calls)
        await self.book.execute(1,self.book.ticket(a),"confirm",lambda *_:True,self.execute)
        self.assertEqual(self.book.pending(1),[b])

    async def test_failure_receipt_is_not_success_and_same_args_not_redispatched(self):
        a=self.propose()
        async def fail(*_): return {"ok":False,"error":"REJECTED"}
        r=await self.book.execute(1,self.book.ticket(a),"confirm",lambda *_:True,fail)
        self.assertFalse(r["ok"]); self.assertEqual(r["outcome"],"failed")
        self.assertIs(self.propose(),a)
        r=await self.book.execute(1,self.book.ticket(a),"retry",lambda *_:True,self.execute)
        self.assertFalse(r["ok"]); self.assertFalse(self.calls)

    async def test_cancel_and_cross_session_ticket(self):
        a=self.propose()
        r=await self.book.execute(2,self.book.ticket(a),"wrong",lambda *_:True,self.execute)
        self.assertFalse(r["ok"])
        self.book.cancel(1)
        r=await self.book.execute(1,self.book.ticket(a),"late",lambda *_:True,self.execute)
        self.assertFalse(r["ok"]); self.assertFalse(self.calls)

    async def test_permission_rechecked_after_proposal(self):
        a=self.propose()
        r=await self.book.execute(1,self.book.ticket(a),"confirm",lambda *_:False,self.execute)
        self.assertFalse(r["ok"]); self.assertFalse(self.calls)

    async def test_unknown_persists_and_blocks_new_task_rephrase(self):
        a=self.propose()
        async def timeout(*_): raise TimeoutError()
        r=await self.book.execute(1,self.book.ticket(a),"confirm",lambda *_:True,timeout)
        self.assertEqual(r["outcome"],"unknown")
        self.book = ActionLedger(self.db)
        b=self.propose(task="new-task")
        self.assertEqual(a["action_id"],b["action_id"])
        r=await self.book.execute(1,self.book.ticket(b),"retry",lambda *_:True,self.execute)
        self.assertFalse(r["ok"]); self.assertFalse(self.calls)

    async def test_crash_during_execution_restores_unknown(self):
        a=self.propose(); a["status"]="executing"; self.book.save(a)
        restored=ActionLedger(self.db)
        self.assertEqual(restored.records[a["action_id"]]["status"],"unknown")

    async def test_double_click_executes_once(self):
        a=self.propose(); ticket=self.book.ticket(a)
        r=await asyncio.gather(*(self.book.execute(1,ticket,"confirm",lambda *_:True,self.execute) for _ in range(2)))
        self.assertEqual(len(self.calls),1)
        self.assertEqual(sum(x["ok"] for x in r),1)

    async def test_caller_mutation_does_not_change_proposal(self):
        args={"path":"x","content":"a"}
        a=self.book.propose(1,"t","r","write_file",args)
        args["content"]="evil"
        self.assertEqual(a["arguments"]["content"],"a")
