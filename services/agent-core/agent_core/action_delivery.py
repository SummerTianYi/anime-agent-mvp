"""User-facing projection of the ledger. Diagnostic envelopes stay in storage."""
from pathlib import PureWindowsPath
import hashlib

from . import public_search
from .tool_contracts import tool_effect

NAMES = {"write_file":"写入文件","run_command":"运行命令","read_file":"读取文件","look_at_screen":"把屏幕截图交给视觉服务分析",
         "get_time":"查看时间","list_dir":"查看目录","read_tool_result":"读取上一段结果","recall_memory":"查询记忆",
         "search_emails":"搜索邮件","read_email":"读取邮件","send_email":"发送邮件","get_file_contents":"读取文件内容",
         "issue_read":"查看议题","issue_write":"更新议题","search":"查询网盘","tavily_search":"搜索公开网页"}
FIELDS = {"to":"收件人","cc":"抄送","bcc":"密送","subject":"主题","body":"正文","content":"内容","path":"文件",
          "command":"命令","args":"参数","query":"查询内容","q":"查询内容","title":"标题","method":"操作类型","repo":"仓库",
          "owner":"所有者","issue_number":"议题号","messageId":"邮件编号","id":"对象编号","mode":"写入方式"}


def value_text(value):
    if isinstance(value,list):
        return "、".join(value_text(v) for v in value)
    if isinstance(value,dict):
        return "，".join(f"{FIELDS.get(k,k)}为{value_text(v)}" for k,v in value.items())
    return str(value)


def describe(tool,args):
    if tool==public_search.TOOL and public_search.valid(args):
        return "查询" + public_search.describe(args)
    name = NAMES.get(tool.rsplit("__",1)[-1], "调用外部服务处理指定内容")
    details = [f"{FIELDS.get(k,k)}为{value_text(v)}" for k,v in args.items()]
    return name + ("（" + "，".join(details) + "）" if details else "")


def pending_text(items):
    if len(items)==1:
        a = items[0]
        return "这项操作待确认。可以" + describe(a["tool"],a["arguments"]) + "吗？"
    lines = [f"{i}. {describe(a['tool'],a['arguments'])}" for i,a in enumerate(items,1)]
    return "有多项操作待确认，请告诉我要办理第几项。\n" + "\n".join(lines)


def problem(result):
    if result.get("outcome")=="unknown":
        return "这项操作的结果未知，我没有重复执行。"
    if result.get("kind"):
        return public_search.failure(result["kind"])
    error = str(result.get("error","")).lower()
    if "禁止发送" in error:
        return "按你的要求，内容没有发送。"
    if "未连接" in error or "不可用" in error:
        return "服务暂时没有连上，这次没有取得结果。"
    if "权限拒绝" in error:
        return "当前权限不允许这项操作，我没有执行。"
    if "拒绝" in error:
        return "这项操作失败了，服务拒绝了请求。"
    if "invalid_grant" in error or "401" in error or "login" in error or "登录" in error:
        return "服务登录已失效，重新登录后才能继续。"
    if "超时" in error or "timeout" in error:
        return "服务响应超时，我没能核实结果。"
    if "api key" in error or "密钥" in error:
        return "服务凭据尚未配置，我暂时无法查询。"
    if "不存在" in error:
        return "没有找到指定的对象，这次没能完成。"
    return "这次操作失败了，服务没有返回可核实的结果。"


def read_value(tool, result):
    if result.get("ok") is not True:
        return problem(result)
    for key in ("local_time","content","text","title","output"):
        value = result.get(key)
        if isinstance(value,str) and value.strip():
            return value
    if isinstance(result.get("entries"),list):
        return "、".join(str(e["name"]) for e in result["entries"] if isinstance(e,dict) and "name" in e) or "目录是空的。"
    return ""


def action_result(item):
    state, tool, args = item["status"],item["tool"],item["arguments"]
    result = item.get("receipt") or {}
    if state in ("failed","unknown"):
        return problem({**result,"outcome":state})
    if state!="succeeded":
        return {"cancelled":"已取消，未执行。","expired":"这项授权已过期，未执行。",
                "executing":"还在处理中，暂时没有最终结果。"}.get(state,"")
    if tool.endswith("send_email"):
        return "邮件服务已接受发送给" + value_text(args.get("to","指定收件人")) + "的邮件。"
    if tool=="write_file":
        target=PureWindowsPath(str(args.get("path",""))).name
        content=args.get("content")
        if result.get("verified_readback") and isinstance(content,str) and args.get("mode","overwrite")=="overwrite":
            binary=content.encode()
            if hashlib.sha256(binary).hexdigest()==result.get("sha256") and len(binary)==result.get("bytes_written"):
                return f"已写入并读回核对《{target}》。内容是：\n{content}"
        return f"已写入《{target}》。"
    if tool_effect(tool,args)=="read":
        return read_value(tool,result)
    return read_value(tool,result) or (describe(tool,args) + "已办理。")
