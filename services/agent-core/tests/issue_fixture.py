"""Synthetic GitHub transport using the previously captured deployed schema."""
import copy
import json
from pathlib import Path

from agent_core.mcp_host import McpServer, McpHost


class SyntheticGitHub(McpServer):
    def __init__(self, number=17):
        super().__init__("github", [])
        self.started = True
        schema = Path(__file__).resolve().parents[3] / "docs/assessments/root-cause-audit/evidence/mcp-schema.json"
        captured = json.loads(schema.read_text(encoding="utf-8"))
        self.tools = [t for s in captured["servers"] if s["server"] == "github"
                      for t in s["tools"] if t["name"] in {"issue_read", "issue_write"}]
        self.target = dict(owner="SummerTianYi", repo="a4-synthetic", issue_number=number)
        self.issue = dict(number=number, html_url=f"https://github.com/SummerTianYi/a4-synthetic/issues/{number}",
                          title="合成初始标题", body="蓝桥记录\n保留原始正文。", state="open",
                          labels=[{"name": "synthetic"}], assignees=[{"login": "synthetic-owner"}],
                          milestone=None, locked=False, state_reason=None)
        self.initial = copy.deepcopy(self.issue)
        self.calls = []
        self.writes = 0
        self.read_transform = None
        self.fail_read_after_write = False
        self.lose_write_receipt = False

    def host(self):
        host = McpHost()
        host.servers["github"] = self
        return host

    async def _roundtrip(self, payload):
        name = payload["params"]["name"]
        args = payload["params"]["arguments"]
        self.calls.append({"tool": name, "arguments": copy.deepcopy(args), "writes_before": self.writes})
        if any(args.get(k) != v for k, v in self.target.items()):
            return {"result": {"isError": True, "content": [{"type": "text", "text": "wrong synthetic target"}]}}
        if name == "issue_write" and args.get("method") == "update":
            self.writes += 1
            # Deliberately apply extra fields too: the host, not this fixture,
            # must reject unintended edits before permission and dispatch.
            self.issue.update({k: copy.deepcopy(v) for k, v in args.items()
                               if k not in {"method", "owner", "repo", "issue_number"}})
            if self.lose_write_receipt:
                raise TimeoutError("synthetic lost write receipt")
        elif name != "issue_read" or args.get("method") != "get":
            raise ValueError("unsupported synthetic operation")
        if name == "issue_read" and self.writes and self.fail_read_after_write:
            raise TimeoutError("synthetic read timeout")
        result = copy.deepcopy(self.issue)
        if name == "issue_read" and self.writes and self.read_transform:
            result = self.read_transform(result)
        self.calls[-1]["returned"] = copy.deepcopy(result)
        return {"result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}}


def request(target, title):
    return (f"请把仓库 {target['owner']}/{target['repo']} 的 Issue #{target['issue_number']} 标题改为「{title}」，"
            "仅修改标题，保留正文、状态、标签、负责人和里程碑等其他用户字段。修改后重新读取同一 Issue 并核验，交付仓库、编号和准确标题。")
