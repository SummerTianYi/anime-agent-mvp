"""Validate a complete tool proposal against the registered schema before dispatch."""

from .tool_contracts import invalid_method

def required_parameters(name, arguments, schema):
    required = set(schema.get("required", []))
    if name == "mcp__github__issue_write" and arguments.get("method") == "update":
        required.add("issue_number")
    return required


def validate_proposal(name, arguments, schemas):
    """Reject malformed proposals before permission, ledger or execution.

    This is a small argument gate for the pilot, not a full JSON Schema engine
    or a proof that arguments express the user's natural-language intention.
    """
    schema = schemas.get(name)
    if schema is None:
        return "工具未在本轮注册"
    if not isinstance(arguments, dict):
        return "工具参数必须是对象"
    if invalid_method(name, arguments):
        return "工具 method 未在本轮注册"
    if name == "read_tool_result":
        # The existing bounded page reader owns ref/offset validation and
        # persists its failed read receipt; do not erase that recovery path.
        return ""
    missing = required_parameters(name, arguments, schema) - arguments.keys()
    if missing:
        return "缺少必要参数：" + "、".join(sorted(missing))
    types = {"string": str, "object": dict, "array": list, "boolean": bool,
             "integer": int, "number": (int, float)}
    for key, value in arguments.items():
        field = schema.get("properties", {}).get(key, {})
        kind = field.get("type")
        if isinstance(kind, str) and kind in types:
            if not isinstance(value, types[kind]) or (kind in {"integer", "number"} and isinstance(value, bool)):
                return "参数类型错误：" + key
        if "enum" in field and value not in field["enum"]:
            return "参数值不在允许范围：" + key
    nonempty = {"path"} if name in {"read_file", "write_file"} else set()
    if name in {"mcp__github__issue_write", "mcp__github__issue_read"}:
        nonempty |= {"owner", "repo"}
        if name.endswith("issue_write") and "title" in arguments:
            nonempty.add("title")
        if "issue_number" in arguments:
            number = arguments["issue_number"]
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                return "issue_number 必须为正整数"
    if any(not isinstance(arguments.get(k), str) or not arguments[k].strip() for k in nonempty):
        return "目标和标题参数不能为空：" + "、".join(sorted(nonempty))
    return ""
