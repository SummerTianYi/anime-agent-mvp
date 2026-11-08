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
_OBJECT = r"(?:文件|目录|文件夹|桌面|屏幕|窗口|剪贴板|本地时间|邮件|邮箱|收件箱|命令|脚本|工具|服务|网页|浏览器|仓库|工单|议题|记忆库|历史记忆|GitHub|Issue\b|MCP\b|https?://|[\w./\\:-]+\.(?:txt|md|csv|json|py)\b)"
_FRAME = r"(?:(?:天依[，, ]*)?(?:请|麻烦|能否|能不能|可否|可以|现在|继续|先|再|顺便|帮忙|替我|帮我|给我|为我|你来|用工具|用|把|将|去|我想让你|我需要你|我想请你|我让你|我请你|让你|请你|你|一下|实际|直接|分别|立刻|马上|同时|在|到|向|对|给|、|\s)*)"
_OPERATION = re.compile(rf"^{_FRAME}(?:{_VERB}.{{0,120}}{_OBJECT}|{_OBJECT}.{{0,80}}{_VERB})",re.I)
_COMMAND_WITH_TARGET = re.compile(rf"^{_FRAME}(?:把|将|在|往|向|给).{{1,90}}{_VERB}.{{0,70}}{_OBJECT}", re.I)
_ENGLISH = re.compile(r"^(?:please |can you |could you |would you )?(?:read|open|write|edit|create|send|run|list|search|show|check)\b.{0,100}\b(?:file|directory|inbox|email|mail|command|script|screen|clipboard|repository|issues?|web|time|[\w.-]+\.txt)\b", re.I)
_INFO = re.compile(r"^(?:假如|假设|如果|资料|引用|原文|示例|举例|翻译|解释|什么叫|为什么|怎么(?:样)?(?:才能|能)?|如何|听说|他说|她说|我刚|我昨天|我今天|昨天我)|(?:是(?:什么)?意思|有何区别|有什么区别|有什么风险|的区别|的原理|应不应该|怎么做的)[？?。！!]*$")
_NO_ACTION = re.compile(r"(?:别|不要|不用|无需|不必)(?:替我|帮我|实际|真的|直接)?(?:操作|执行|动手|打开|读取|发送|写入|调用)|(?:只|仅)(?:是)?(?:解释|讨论|举例|聊聊|问问)")
_SEP = re.compile(r"[。！？!?；;\n]+|[，,](?=(?:顺便|另外|同时|再帮我|也请|然后请|但|不过|帮我|请你))")
_PREFIX = re.compile(r"^(?:顺便|另外|同时|也请|然后|还有)[，, ]*")
_BODY = re.compile(r"(?:正文|内容|标题)(?:为|是|如下)?\s*[:：]")
_CONTROL_TARGET = re.compile(r"操作|任务|待办|确认|执行|发送|写入|邮件|文件|参数|票据|旧的|旧版|收件人|正文|\b(?:send|write|execute|run|cancel)\b",re.I)
_SHORT_STOP = re.compile(r"^(?:(?:请|先|就|还是|我)?(?:取消|撤销|算了|拒绝|不同意|不确认|别执行|停下|停止|放弃|不要了|不用了)|no|stop|cancel)[吧了。！! ]*$",re.I)
_CONTINUE = re.compile(r"^(?:请)?(?:继续(?:吧|执行|刚才的.{0,16}任务)?|接着做|go on|continue)[!。！\s]*$",re.I)


@dataclass(frozen=True)
class Route:
    chat: str = ""
    operation: str = ""
    control: str = "other"


def classify(text: str, *, pending: bool, active: bool, status: bool = False, control_text: str | None = None) -> Route:
    """Require an instruction about an external target. Quotes and data are inert."""
    clean = _QUOTED.sub(" ", text).strip()
    choice = decision(control_text if control_text is not None else text)
    control = clean if control_text is None else control_text
    simple = re.sub(r"\s+", "", clean)
    if status or (choice == "approve" and (pending or simple.rstrip("。！!") in {"确认","确认执行","同意执行","执行吧"})):
        return Route(operation=text, control=choice if not status else "other")
    if active and choice in {"decline","edit"} and (
            _SHORT_STOP.fullmatch(simple) or (_CONTROL_TARGET.search(control) and re.search(r"取消|撤销|改为|改成|换成|拒绝|不\s*确认|不同意|(?:别|不要|先不|不再|不)(?:再)?(?:执行|发送|写入)|\b(?:cancel|stop|don\x27t send|do not send)\b",control,re.I)) or
            (pending and re.match(r"^(?:请)?(?:改为|改成|换成)", clean))):
        return Route(operation=text, control=choice)
    if _CONTINUE.fullmatch(clean) and active:
        return Route(operation=text)
    if re.match(r"^(?:引用资料|资料原文|原文|引用)[：:]",clean):
        return Route(chat=text)
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
    chats, operations = [], []
    for original, plain in segments:
        clause = _PREFIX.sub("", plain).strip()
        explicit = (_OPERATION.search(clause) or _COMMAND_WITH_TARGET.search(clause) or _ENGLISH.search(clause)
                    or re.match(r"^(?:请|帮我)?(?:截图|截个图|读屏|报时)[吧。！! ]*$", clause))
        if explicit and not (_INFO.search(clause) or _NO_ACTION.search(clause)):
            operations.append(original)
        elif original:
            chats.append(original)
    if not operations:
        return Route(chat=text)
    return Route("".join(chats).strip(), "".join(operations).strip())


@dataclass
class Turn:
    session: int
    request: str
    mixed: bool = False
    task: str | None = None
    revoked: bool = False


current: ContextVar[Turn | None] = ContextVar("chat_turn", default=None)
lane: ContextVar[str] = ContextVar("chat_lane", default="companion")


def memory_claim_free(body: str, *, attempted: bool) -> str:
    """Remove a first-person persistence promise when the host cannot verify it."""
    clauses = re.split(r"(?<=[。！？!?；;，,])|\n", body)
    claim = re.compile(r"(?:我|已经|已|会|帮你|替你|给你|放心|记住了|记下了|记好啦|记牢了).{0,12}(?:记住|记下|记牢|记好|保存|存好|存下)|^(?:记住|记下|记牢|记好|保存好)[了啦咯]")
    durable = re.compile(r"长期记忆|(?:存|保存|写|录)入.{0,5}记忆|(?:下次|以后|下次见面).{0,10}(?:记得|记住)|已经帮你记住")
    return "".join(s for s in clauses if not ((attempted or durable.search(s)) and claim.search(s))).strip(" \n，,；;")
