"""Gmail 1.1.11 wire envelope, with an independently inspectable mailbox.

No target/scope guard: wrong recipients and every duplicate are accepted here
so tests must detect product failures instead of relying on a benevolent tool.
"""
import copy
import json
from pathlib import Path

from agent_core.mcp_host import McpHost, McpServer

SEND = "mcp__gmail__send_email"


def request(to, subject, body):
    return (f"请向 {to} 发送一封纯文本邮件，仅此一个收件人。主题为「{subject}」。"
            f"请发送后交付准确的发送回执。正文如下（两行，末尾无换行）：\n{body}")


class SyntheticGmail(McpServer):
    def __init__(self, mailbox_path=None):
        super().__init__("gmail", [])
        self.started = True
        schema = Path(__file__).resolve().parents[3] / "docs/assessments/root-cause-audit/evidence/mcp-schema.json"
        captured = json.loads(schema.read_text(encoding="utf-8"))
        self.tools = [t for s in captured["servers"] if s["server"] == "gmail"
                      for t in s["tools"] if t["name"] == "send_email"]
        self.calls, self.mailbox = [], []
        self.mailbox_path = mailbox_path
        self.error = None
        self.lose_receipt = False
        self.success_override = None

    def host(self):
        host = McpHost()
        host.servers["gmail"] = self
        return host

    async def _roundtrip(self, payload):
        args = copy.deepcopy(payload["params"]["arguments"])
        self.calls.append({"tool": payload["params"]["name"], "arguments": args})
        if self.error:
            text = "Error: " + self.error
        else:
            message_id = f"19abc{len(self.mailbox)+1:011x}"
            self.mailbox.append({"id": message_id, "arguments": args,
                                 "recipients": args.get("to", []) + args.get("cc", []) + args.get("bcc", [])})
            if self.mailbox_path:
                self.mailbox_path.write_text(json.dumps(self.mailbox, ensure_ascii=False, indent=2), encoding="utf-8")
            if self.lose_receipt:
                raise TimeoutError("synthetic accepted but response lost")
            text = self.success_override if self.success_override is not None else f"Email sent successfully with ID: {message_id}"
        result = {"content": [{"type": "text", "text": text}]}
        self.calls[-1]["returned"] = copy.deepcopy(result)
        return {"result": result}
