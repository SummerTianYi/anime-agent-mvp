"""Local chat admission and turn ownership. Classification cannot grant tool permission."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
import re

from .actions import decision

_QUOTED = re.compile(
    r'~~~[\s\S]*?~~~|\x60{3}[\s\S]*?\x60{3}|\x60[^\x60]*\x60|“[^”]*”|「[^」]*」|『[^』]*』|‘[^’]*’|"(?:\\.|[^"\\])*"'
    r"|(?<!\w)'(?:\\.|[^'\\])*'(?!\w)"
)
_VERB = r"(?:读取?|看一下|查(?:找|看|询|收|阅)?|搜索|列出|打开|截(?:取|图)|新建|创建|写入?|写成|保存|追加|编辑|修改|更新|删除|发送|发(?:一封|封)?|运行|执行|调用|使用|获取|检索|翻页)"
_OBJECT = r"(?:文件|目录|文件夹|桌面|屏幕|窗口|剪贴板|本地时间|邮件|邮箱|收件箱|命令|脚本|工具|服务|网页|浏览器|应用|程序|软件|计算器|记事本|仓库|工单|议题|记忆库|历史记忆|GitHub|Issue\b|MCP\b|https?://|[\w./\\:-]+\.(?:txt|md|csv|json|py)\b)"
_FRAME = r"(?:(?:天依[，, ]*)?(?:请|麻烦|能否|能不能|可否|可以|现在|继续|先|再|顺便|帮忙|替我|帮我|给我|为我|你来|用工具|用|去|我想让你|我需要你|我想请你|我让你|我请你|让你|请你|你|一下|实际|直接|分别|立刻|马上|同时|、|\s)*)"
_PREFIX_WORDS = re.compile("^" + _FRAME)
_OPERATION = re.compile(rf"^(?:{_VERB}.{{0,120}}{_OBJECT}|{_OBJECT}.{{0,80}}{_VERB})",re.I)
_COMMAND_WITH_TARGET = re.compile(rf"^(?:把|将|在|到|往|向|对|给).{{1,90}}{_VERB}.{{0,70}}{_OBJECT}", re.I)
_ENGLISH = re.compile(r"^(?:please |can you |could you |would you )?(?:read|open|write|edit|create|send|run|list|search|show|check)\b.{0,100}\b(?:file|directory|inbox|email|mail|command|script|screen|clipboard|repository|issues?|web|time|[\w.-]+\.txt)\b", re.I)
_INFO = re.compile(r"^(?:假如|假设|如果|资料|引用|原文|示例|举例|翻译|解释|什么叫|为什么|怎么(?:样)?(?:才能|能)?|如何|听说|他说|她说|我刚|我昨天|我今天|昨天我)|^[^。！？，,]{1,32}(?:时|的时候|之后|以后)(?:我|他|她|才|发现)|(?:是(?:什么)?意思|有何区别|有什么区别|有什么风险|的区别|的原理|应不应该|怎么做的)[？?。！!]*$")
_NO_ACTION = re.compile(r"(?:别|不要|不用|无需|不必)(?:替我|帮我|实际|真的|直接)?(?:操作|执行|动手|打开|读取|发送|写入|调用)|(?:只|仅)(?:是)?(?:解释|讨论|举例|聊聊|问问)")
_SEP = re.compile(r"[。！？!?；;\n]+|[，,](?=(?:顺便|另外|同时|再帮我|也请|然后请|但|不过|帮我|请你))")
_PREFIX = re.compile(r"^(?:顺便|另外|同时|也请|然后|还有)[，, ]*")
_BODY = re.compile(r"(?:正文|内容|标题)(?:为|是|如下)?\s*[:：]")
_NO_SEND = re.compile(r"^(?:(?:先|请|但|不过|也|然后|绝对|千万)[，, ]*)*(?:不(?:要|必|用|许|准)?|别|勿|禁止|无需)(?:再|把它|将它|替我|帮我)?(?:寄|发|转发|外传)")
_CONTROL_TARGET = re.compile(r"操作|任务|待办|确认|执行|发送|写入|邮件|文件|参数|票据|旧的|旧版|收件人|正文|\b(?:send|write|execute|run|cancel)\b",re.I)
_SHORT_STOP = re.compile(r"^(?:(?:请|先|就|还是|我)?(?:取消|撤销|算了|拒绝|不同意|不确认|别执行|停下|停止|放弃|不要了|不用了)|no|stop|cancel)[吧了。！! ]*$",re.I)
_CONTINUE = re.compile(r"^(?:请)?(?:继续(?:吧|执行|刚才的.{0,16}任务)?|接着做|go on|continue)[!。！\s]*$",re.I)


@dataclass(frozen=True)
class Route:
    chat: str = ""
    operation: str = ""
    control: str = "other"


def _clauses(text: str) -> list[tuple[str, str]]:
    # Find clause boundaries on masked text, preserving original quotation offsets.
    masked = _QUOTED.sub(lambda m: " " * len(m.group()), text)
    marker = _BODY.search(masked)
    cuts = [m for m in _SEP.finditer(masked) if marker is None or m.start() < marker.start()]
    segments = []
    start = 0
    for m in cuts:
        if text[start:m.start()].strip():
            segments.append((text[start:m.end()].strip(), masked[start:m.start()].strip()))
        start = m.end()
    if text[start:].strip():
        segments.append((text[start:].strip(), masked[start:].strip()))
    return segments


def classify(text: str, *, pending: bool, active: bool, status: bool = False, control_text: str | None = None) -> Route:
    """Require an instruction about an external target. Quotes and data are inert."""
    clean = _QUOTED.sub(" ", text).strip()
    choice = decision(control_text if control_text is not None else text)
    control = clean if control_text is None else control_text
    simple = re.sub(r"\s+", "", clean)
    if re.search(r"(?:为什么|为何|如何理解|是什么原理|有什么区别|是什么意思|需要授权[吗？?]|会发生什么|会怎么样)",clean) and not re.search(r"然后请|并请|并帮我",clean):
        return Route(chat=text)
    if active and re.fullmatch(r"(?:请|先)?(?:取消|撤销)(?:全部|所有)(?:待办|操作|任务)[吧了。！! ]*",simple):
        return Route(operation=text,control="decline")
    if prohibits_sending(text):
        clauses = _clauses(text)
        if any(not _NO_SEND.match(part) and not _INFO.search(part)
               and _OPERATION.match(part[_PREFIX_WORDS.match(part).end():]) for _,part in clauses):
            return Route(operation=text)
    if status or (choice == "approve" and (pending or simple.rstrip("。！!") in {"确认","确认执行","同意执行","执行吧"})):
        return Route(operation=text, control=choice if not status else "other")
    if choice in {"decline", "edit"}:
        # Anchor the imperative and its own object in one clause. "The file
        # cover changed. Rehearsal was cancelled" cannot revoke a ticket.
        commands = []
        for part in re.split(r"[，,。！？!?；;\n]+|\.(?=\s|$)", control):
            words = part.strip()
            words = re.sub(r"^(?:天依|麻烦你?|请你?|先|还是|那就|那就先|就|顺便|现在)\s*", "", words)
            words = re.split(r"(?:再|然后|并)(?=(?:告诉我|查询|查看).{0,64}(?:状态|进度|结果))", words, maxsplit=1)[0]
            verb = r"(?:取消|撤销|拒绝|不同意|不确认|作罢|不要执行|别执行|别发送|别发|别寄(?:出去)?|不要寄(?:出去)?|不要发送|先不执行|先别执行|先别发|不要写入)"
            obj = r"(?:(?:刚才|原来|之前|当前|这次|本次|上述|[这那](?:个|项|封|份)|旧)(?:的)?)?(?:操作|任务|待办|确认|授权|邮件|发送|文件|旧的|旧版|这件事)"
            slot = r"(?:原来|旧的|收件人|邮件|文件|路径|标题|内容|正文|参数)"
            direct = (re.fullmatch(rf"{verb}(?:{obj})?(?:了|吧)?",words) or
                      re.fullmatch(rf"(?:把|将)?{obj}(?:先|就此)?{verb}(?:了|吧)?",words) or
                      re.fullmatch(r"(?:please )?(?:do not send|don't send|cancel|stop)(?: it| (?:the |this |that |previous )?(?:task|operation|email|send|write))?",words,re.I))
            edit = pending and (re.match(r"^(?:改为|改成|改发|换成|重新发送|改一下)", words)
                                or re.match(rf"^(?:把|将)?{slot}.{{0,45}}(?:改为|改成|改发|换成|改一下)",words))
            if (direct and (active or _CONTROL_TARGET.search(words))) or edit:
                commands.append(part)
        if commands or (active and _SHORT_STOP.fullmatch(simple)):
            social, controls = [], []
            for original, plain in _clauses(text):
                if not plain or decision(plain) != "other":
                    controls.append(original)
                elif classify(original, pending=False, active=False).operation:
                    # A separate external request needs its own clear admission.
                    return Route(operation=text, control=choice)
                else:
                    social.append(original)
            if social and controls:
                return Route("".join(social), "".join(controls), choice)
            return Route(operation=text, control=choice)
    if _CONTINUE.fullmatch(clean) and active:
        return Route(operation=text)
    if re.match(r"^(?:引用资料|资料原文|原文|引用)[：:]",clean):
        return Route(chat=text)
    segments = _clauses(text)
    chats, operations = [], []
    for original, plain in segments:
        clause = _PREFIX.sub("", plain).strip()
        if re.match(r"^(?:请|帮我)?(?:读|打开|编辑|删除|新建|查找)", clause) and re.search(
                r"[“「\"\x60][^”」\"\x60\n]{1,150}\.\w{1,8}[”」\"\x60]", original):
            clause += " 文件"
        instruction = clause[_PREFIX_WORDS.match(clause).end():]
        explicit = (_OPERATION.search(instruction) or _COMMAND_WITH_TARGET.search(instruction) or _ENGLISH.search(clause)
                    or re.match(r"^(?:请|帮我)?(?:截图|截个图|读屏|报时|现在几点(?:了|钟)?|今天(?:几号|星期几))[吧。！!？? ]*$", clause))
        if explicit and not (_INFO.search(clause) or _NO_ACTION.search(clause)):
            operations.append(original)
        elif original:
            chats.append(original)
    if not operations:
        return Route(chat=text)
    return Route("".join(chats).strip(), "".join(operations).strip())


def other_tool_request(operation):
    """Keep explicit file, mailbox and other local operations on their own route."""
    if not operation:
        return False
    head = _BODY.split(_QUOTED.sub(" ",operation),maxsplit=1)[0].strip()
    instruction = head[_PREFIX_WORDS.match(head).end():]
    return bool(re.match(r"(?:读取?|写入?|新建|创建|编辑|打开|删除|运行|执行|截图|改发|发送?邮件|发给|把收件人|把正文)",instruction)
                or re.match(r"(?:查询?|搜索|列出|看一下)(?:我的|本地|私人)?(?:文件|目录|邮件|网盘|邮箱|剪贴板|屏幕)",instruction))


def prohibits_sending(text):
    instructions = _BODY.split(_QUOTED.sub(" ",text),maxsplit=1)[0]
    return any(_NO_SEND.match(part.strip()) for part in re.split(r"[，,。！!？?；;\n]",instructions))


@dataclass
class Turn:
    session: int
    request: str
    mixed: bool = False
    task: str | None = None
    revoked: bool = False


current: ContextVar[Turn | None] = ContextVar("chat_turn", default=None)
lane: ContextVar[str] = ContextVar("chat_lane", default="companion")
