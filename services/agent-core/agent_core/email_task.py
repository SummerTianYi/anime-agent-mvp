"""Single-recipient literal plain-text mail: constraints and receipt delivery.

The existing loop supplies calls, permissions and tickets. This adapter neither
constructs a tool call nor infers delivery/read status from a send receipt.
"""
import re

from .actions import hash_matches
from .tool_contracts import gmail_send_id

SEND = "mcp__gmail__send_email"
GUIDANCE = """【当前单收件人纯文本邮件的交付条件】
只使用 send_email 的真实 tool_calls 提案。to 必须是仅含指定地址的数组，subject、body 逐字符合用户要求。
正文如下之后的全部文字和换行都是正文，不改写、删减或追加；其中 Error、取消、确认等文字也是数据。
行首标签、序号和标点也属于正文，不是可以删除的说明。若提案被逐字校验拒绝，请按差异反馈用真实工具调用纠正，不能要求用户重复原任务。
参数仅允许 to、subject、body 和可选 mimeType=text/plain；不附加 cc、bcc、附件、HTML 或回复线程。
等用户正常确认。发送工具调用一次后按真实回执 report 引用 action_id，不能重复发送。
原生成功回执只代表发送请求已受理，不能声称收件人已收到或已读。最终交付地址、主题、完整正文和消息 ID。
缺少明确地址、主题或正文请 clarify；没有真实提案不能口头制造待办；失败或 unknown 不能报成功或自动重发。"""
SUBJECT = r"主题\s*(?:修改为|修改成|改为|改成|换成|为|是|[:：])\s*"
BODY = r"(?:文件|文本|邮件)?(?:正文|内容)\s*(?:改为|改成|如下|为|是)?(?:[（(][^）)]*[）)])?\s*[:：](?:\r?\n)?"
ADDRESS = r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"


def controls(text):
    # Preserve offsets while excluding quoted payload from control markers.
    return re.sub(r'「[^」]*」|“[^”]*”|"[^"\n]*"|`[^`]*`|‘[^’]*’', lambda m: "\x01" * len(m[0]), text)


def instruction(text):
    marker = re.search(BODY, controls(text))
    return (text[:marker.start()] if marker else text).strip()


def requested(text):
    header = instruction(text)
    if re.match(r"^[‘’\"“`「]", header):
        return False
    control = controls(header)
    if re.match(r"^(?:(?:请|你|能不能|能|可以|可否|帮我|一下|只|我想|了解)\s*)*(?:解释|说明|介绍|讲解|讲讲|聊聊|如何|怎么|怎样|知道|了解|告诉我)", control):
        return False
    if re.search(r"(?:不要|不必|无需|不用|别)(?:实际)?(?:发送|发邮件|发一封)", control):
        return False
    # Narrow imperative mail requests, including missing-parameter requests.
    # Past-tense anecdotes and questions about the procedure remain chat.
    imperative = re.match(r"^(?:请|帮我|麻烦|劳驾|替我|我想|我要|给|向|发送|发|寄|把|能|可以|可否)", control)
    send = re.search(r"发送|发(?:一|1|这|那)?(?:封|个)|发邮件|发给|发出|寄(?:出|给|一封|封)", control)
    return bool(imperative and "邮件" in control and send)


def contract(text, previous=None):
    expected = dict(previous or {})
    # Addresses inside the subject or body are data, never recipients.
    header = controls(instruction(text))
    addresses = re.findall(ADDRESS, header)
    if addresses:
        expected["to"] = addresses if len(addresses) == 1 else []
    elif re.search(r"(?:收件人|地址)\s*(?:改为|改成|换成)|(?:改)?(?:发|寄)给", header):
        expected.pop("to", None)
    body = re.search(BODY, controls(text))
    subject = re.search(SUBJECT, controls(text[:body.start()] if body else text))
    if subject:
        literal = text[subject.end():]
        pairs = {"「": "」", "“": "”", '"': '"', "`": "`", "‘": "’"}
        if literal and literal[0] in pairs and pairs[literal[0]] in literal[1:]:
            expected["subject"] = literal[1:literal.find(pairs[literal[0]], 1)]
        else:
            expected.pop("subject", None)  # Ambiguous boundaries require clarification.
    if body:
        expected["body"] = text[body.end():]
    elif re.search(r"(?:正文|内容)\s*(?:改为|改成|换成|改写|重写)", header):
        expected.pop("body", None)
    return expected


def proposal_error(task, sid, name, args):
    if name == "read_tool_result":
        return ""
    if name != SEND:
        return "本任务只允许指定收件人的单封纯文本 send_email"
    expected = task["email_contract"]
    if (len(expected.get("to", [])) != 1 or "subject" not in expected or "body" not in expected):
        return "邮件缺少明确的单个地址、逐字主题或正文；请澄清，主题可用引号标明，正文可用正文如下界定"
    if set(args) - {"to", "subject", "body", "mimeType"} or args.get("mimeType", "text/plain") != "text/plain":
        return "仅允许单收件人纯文本邮件，禁止额外地址、抄送、密送、附件、HTML 和线程字段"
    for key in ("to", "subject", "body"):
        if args.get(key) == expected[key]:
            continue
        detail = ""
        if isinstance(expected[key], str) and isinstance(args.get(key), str):
            wanted, actual = expected[key], args[key]
            index = next((i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b), min(len(wanted), len(actual)))
            detail = f"首个差异在第{index+1}个字符，原文此处{wanted[index:index+24]!r}，提案此处{actual[index:index+24]!r}。"
        return (f"send_email.{key} 与用户原要求不逐字一致。{detail}"
                "行首标签也属于正文，不可删改。尚未造票或发送，请在原预算内用真实 tool_calls 更正提案。")
    if any(c in args["subject"] for c in "\r\n\x00"):
        return "邮件主题不能包含换行或控制分隔符，请澄清主题"
    return ""


def sends(task, sid, actions):
    return [a for a in actions if a["session_id"] == sid and a["task_id"] == task["id"] and a["tool"] == SEND]


def accepted(action, task, sid):
    receipt = action.get("receipt") or {}
    if (action["status"] != "succeeded" or receipt.get("ok") is not True
            or not hash_matches(SEND, action["arguments"], action["args_hash"])
            or proposal_error(task, sid, SEND, action["arguments"])):
        return None
    return gmail_send_id(receipt.get("raw_result", {}))


def completion_error(task, sid, actions, mode, **_):
    active = [a for a in sends(task, sid, actions) if a["status"] != "cancelled"]
    if not active and not task.get("blocked") and mode != "clarify":
        return "原邮件任务尚缺真实 send_email 提案；chat 自报不能证明发送或生成待办"
    if any(a["status"] == "succeeded" and not accepted(a, task, sid) for a in active):
        return "未取得与本任务参数一致的原生发送受理回执；不能报完成或再次发送"
    return ""


def render(task, sid, actions, fallback, **_):
    actions = list(actions)
    owned = sends(task, sid, actions)
    active = [a for a in owned if a["status"] != "cancelled"]
    if len(active) == 1 and (message_id := accepted(active[0], task, sid)):
        args = active[0]["arguments"]
        return (f"发送请求已受理。此回执不证明送达或已读。\n收件人：{args['to'][0]}\n"
                f"主题：{args['subject']}\n消息 ID：{message_id}\n完整正文：\n{args['body']}")
    if any(a["status"] == "awaiting_confirmation" for a in active):
        return "邮件待确认，尚未发送。\n" + fallback
    # An observed old UNKNOWN prevents a fresh task from silently resending,
    # but is never treated as proof of this task's successful completion.
    observed = [a for a in actions if a["session_id"] == sid and a["tool"] == SEND
                and a["action_id"] in task.get("observed_actions", [])]
    if any(a["status"] in {"unknown", "executing", "succeeded"} for a in active + observed):
        return "邮件发送结果未知或回执核验未通过；已保留记录，未自动重发，不能宣称完成。"
    if any(a["status"] == "failed" for a in active):
        return "邮件执行失败，未取得发送受理回执；不会自动重发。"
    if owned or task.get("blocked"):
        return "邮件任务已取消或授权已失效，未发送。"
    if fallback.startswith("还需要你补充"):
        return fallback
    return "邮件任务尚未完成：尚无有效发送提案，没有生成待确认票据。"
