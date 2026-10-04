"""Codex: offline mail/GitHub MCP with durable synthetic receipts; no network."""
import json
from pathlib import Path
import sys


def schema(name, description, fields, required):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": fields, "required": required}}


S = {"type": "string"}
TOOLS = [
    schema("search_emails", "搜索邮件并返回ID和主题；正文需read_email读取。",
           {"query": S, "maxResults": {"type": "integer"}}, ["query"]),
    schema("read_email", "读取指定邮件的完整正文。", {"messageId": S}, ["messageId"]),
    schema("send_email", "发送邮件。实际发送前由宿主确认。", {"to": {"type": "array", "items": S},
           "subject": S, "body": S}, ["to", "subject", "body"]),
    schema("get_file_contents", "读取GitHub仓库文件正文。", {"owner": S, "repo": S, "path": S},
           ["owner", "repo", "path"]),
    schema("create_issue", "创建GitHub issue并返回编号和链接。", {"owner": S, "repo": S,
           "title": S, "body": S}, ["owner", "repo", "title", "body"]),
]


def execute(state, name, args):
    error = state.get("faults", {}).get(name)
    if error:
        return {"isError": True, "content": [{"type": "text", "text": str(error)}]}
    if name == "search_emails":
        value = [{"id": m["id"], "subject": m["subject"], "from": m["from"]}
                 for m in state["mail"]["messages"]]
    elif name == "read_email":
        value = next((m for m in state["mail"]["messages"] if m["id"] == args.get("messageId")), None)
        if value is None:
            return {"isError": True, "content": [{"type": "text", "text": "MAIL_NOT_FOUND"}]}
    elif name == "send_email":
        if not isinstance(args.get("to"), list) or not args["to"] or not all(
                str(a).endswith("@example.invalid") for a in args["to"]):
            return {"isError": True, "content": [{"type": "text", "text": "SYNTHETIC_ADDRESS_REQUIRED"}]}
        value = {"id": "sent-" + str(len(state["mail"]["outbox"]) + 1),
                 **{k: args.get(k) for k in ("to", "subject", "body")}, "status": "sent"}
        state["mail"]["outbox"].append(value)
    elif name in {"get_file_contents", "create_issue"}:
        gh = state["github"]
        if args.get("owner") != gh["owner"] or args.get("repo") != gh["repo"]:
            return {"isError": True, "content": [{"type": "text", "text": "REPOSITORY_NOT_FOUND"}]}
        if name == "create_issue":
            number = len(gh["issues"]) + 1
            value = {"number": number, "title": args.get("title"), "body": args.get("body"),
                     "url": "https://github.invalid/fixture-owner/fixture-repo/issues/" + str(number)}
            gh["issues"].append(value)
        else:
            path = args.get("path")
            if path not in gh["files"]:
                return {"isError": True, "content": [{"type": "text", "text": "FILE_NOT_FOUND"}]}
            value = gh["files"][path]
            if state.get("faults", {}).get("github_embedded_resource"):
                return {"content": [{"type": "text", "text": "File fetched; content attached as resource."},
                                    {"type": "resource", "resource": {
                                        "uri": "fixture://repo/README.md", "mimeType": "text/plain", "text": value}}]}
    else:
        return {"isError": True, "content": [{"type": "text", "text": "UNKNOWN_TOOL"}]}
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}


def serve(state_file, domain):
    state_file = Path(state_file)
    for line in sys.stdin:
        msg = json.loads(line)
        method, ident = msg.get("method"), msg.get("id")
        if ident is None:
            continue
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "harness-v0-" + domain, "version": "0.1"}}
        elif method == "tools/list":
            allowed = {"search_emails", "read_email", "send_email"} if domain == "gmail" else {"get_file_contents", "create_issue"}
            result = {"tools": [t for t in TOOLS if t["name"] in allowed]}
        elif method == "tools/call":
            state = json.loads(state_file.read_text(encoding="utf-8"))
            params = msg.get("params", {})
            name, args = params.get("name"), params.get("arguments", {})
            try:
                result = execute(state, name, args)
            except Exception as exc:
                result = {"isError": True, "content": [{"type": "text", "text": type(exc).__name__}]}
            receipt = {"execution_id": domain + "-" + str(ident), "rpc_id": ident,
                       "server": domain, "tool": name, "arguments": args, "result": result}
            state.setdefault("receipts", []).append(receipt)
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            result = {}
        print(json.dumps({"jsonrpc": "2.0", "id": ident, "result": result}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    serve(sys.argv[1], sys.argv[2])
