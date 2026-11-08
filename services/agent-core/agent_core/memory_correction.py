"""Bounded, source-grounded corrections; no model ID or similarity authorizes a write.

Legacy strings are parsed only when needed. Unrecognised/ambiguous records stay
intact. Offsets refer to the original string so a compound fact loses no text.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


ATTRIBUTES = (
    "最喜欢的颜色", "最喜欢的歌手", "最喜欢的水果", "截止日期", "负责人",
    "预算", "日期", "地点", "代号", "颜色", "生日", "职业", "称呼", "城市", "名字",
)
_ATTR = "(?:" + "|".join(ATTRIBUTES) + ")"
_CLAUSE = re.compile(rf"(?P<entity>.*?)\s*(?P<attribute>{_ATTR})\s*(?:是|为|等于|[:：=])?\s*(?P<value>.+)")
_CUE = re.compile(r"更正|纠正|修正|更新为|调整为|调整到|改为|改成|改到|改一下|记错|不是.+(?:而是|是)|应为|应是|实际是|实际上是")
_LOCAL = re.compile(r"(?:仅|只)(?:在|限于)?(?:本次|这次|当前|这个)(?:会话|聊天)(?:内|中)?(?:生效|有效)?")
_REFERENCE = re.compile(r"资料|引用|原文|转述|举例|例句|翻译|解释|假如|假设|如果|是否|怎么|如何|不要|别改|不更正|不修改|[?？]|[『「“\"`]")
_ENTITY = re.compile(r"[\w\u4e00-\u9fff·\-]{1,48}")
_UNSAFE_VALUE = re.compile(r"[，,；;。\n]|以及|分别|不是|改为|改成|更正|记住|待确认|[（）()]|[『「“\"`]")


@dataclass(frozen=True)
class Part:
    entity: str
    attribute: str
    value: str
    start: int
    end: int


def entity_key(value: str) -> str:
    return re.sub(r"(?:的|项目)$", "", value.strip())


def parts(content: str) -> list[Part]:
    """Return all clauses or none; never guess a decomposition of prose."""
    result: list[Part] = []
    previous = ""
    for segment in re.finditer(r"[^，,；;。\n]+", content):
        raw = segment.group()
        if not raw.strip():
            continue
        match = _CLAUSE.fullmatch(raw.strip())
        if not match:
            return []
        entity = match["entity"].strip().removesuffix("的").strip() or previous
        value = match["value"].strip()
        if (not _ENTITY.fullmatch(entity) or any(c in entity for c in ("和", "与", "及"))
                or not value or _UNSAFE_VALUE.search(value)):
            return []
        start = segment.start() + len(raw) - len(raw.lstrip()) + match.start("value")
        result.append(Part(entity_key(entity), match["attribute"], value, start, start + len(value)))
        previous = entity
    keys = [(p.entity, p.attribute) for p in result]
    return result if len(keys) == len(set(keys)) else []


@dataclass(frozen=True)
class Request:
    entity: str
    attribute: str
    new_value: str
    old_value: str | None
    local: bool


def is_reference(text: str) -> bool:
    return bool(_REFERENCE.search(text))


def session_only(text: str) -> bool:
    return bool(_LOCAL.search(text))


def correction_is_in_payload(text: str) -> bool:
    """A file or message body can quote a correction without requesting it."""
    marker = re.search(r"(?:正文|内容|标题)(?:如下|改为|改成|为|是)?\s*[:：]", text)
    return marker is not None and not _CUE.search(text[:marker.start()])


def parse_request(text: str) -> Request | str | None:
    """None is ordinary chat, a string is a non-mutating clarification."""
    if not _CUE.search(text):
        return None
    if re.search(r"资料|引用|原文|转述|举例|例句|翻译|解释|假如|假设|如果", text):
        return None
    if re.search(r"不要|别改|不更正|不修改", text):
        return "本轮没有修改记忆，保留原值。"
    # Quotes around an explicitly named object are not quoted instructions.
    # Other quotation shapes remain non-executable and require clarification.
    text = re.sub(rf"^((?:(?:请|麻烦|帮我|天依)[，,\s]*)*(?:把|将)?)[『「“\"]([^』」”\"\n]+)[』」”\"](?=的?{_ATTR})",
                  r"\1\2", text)
    text = re.sub(r"[，,]\s*(?:可以吗|好吗|行吗)[?？。\s]*$", "", text)
    if re.search(r"是否|怎么|如何|[?？]|[『「“\"`]", text):
        return "尚未更正：请明确这是要修改已有记忆的指令，并说明对象、属性和新值。"
    if re.search(r"对不对|是不是|还是|可能|也许|大概|似乎|好像|(?:吗|么|吧)[。！!\s]*$", text):
        return "尚未更正：这句话可能是询问或不确定陈述。请明确确认对象、属性和新值后再更正。"
    local = bool(_LOCAL.search(text))
    clean = _LOCAL.sub("", text).strip(" ，,。！!\n")
    clean = re.sub(r"^(?:(?:请|麻烦|帮我|天依)[，,\s]*)+", "", clean)
    clean = re.sub(r"^(?:更正|纠正)(?:一下)?[：:，,\s]*", "", clean)
    clean = re.sub(r"^(?:之前|刚才)?(?:记错了|说错了)[，,：:\s]*", "", clean)
    clean = re.sub(r"^(?:请)?(?:把|将)", "", clean).strip()
    # A single explicit entity and property must precede the operation.
    match = re.fullmatch(rf"(?P<entity>.*?)\s*(?P<attribute>{_ATTR})\s*(?P<change>.+)", clean)
    clarify = "尚未更正。请明确要更正的对象、属性和新值；一次更正一项已有记忆。"
    if not match:
        return clarify
    entity = match["entity"].strip().removesuffix("的").strip()
    if not _ENTITY.fullmatch(entity) or any(c in entity for c in ("和", "与", "及")):
        return clarify
    change = match["change"]
    old: str | None = None
    parsed = re.fullmatch(r"(?:从|由)(.+?)(?:更正为|纠正为|改为|改成|改到)(.+)", change)
    if not parsed:
        parsed = re.fullmatch(r"不是(.+?)[，,]\s*(?:而是|是)(.+)", change)
    if parsed:
        old, new = (s.strip() for s in parsed.groups())
    else:
        parsed = re.fullmatch(r"(?:更正为|纠正为|修正为|更新为|调整为|调整到|改为|改成|改到|应为|应是|实际是|实际上是|是|为)\s*(.+)", change)
        if not parsed:
            return clarify
        new = parsed[1].strip()
    if not new or len(new) > 100 or _UNSAFE_VALUE.search(new) or (old is not None and _UNSAFE_VALUE.search(old)):
        return clarify
    return Request(entity_key(entity), match["attribute"], new, old, local)


def resolve(text: str, rows: list[dict[str, Any]], session_id: int) -> dict[str, Any] | None:
    request = parse_request(text)
    if request is None:
        return None
    if isinstance(request, str) and not (any(attribute in text for attribute in ATTRIBUTES)
                                        or re.search(r"记忆|记错", text)):
        # "改成新版" can edit a pending file/Issue/mail task. An incomplete
        # memory request must still identify a memory property or memory itself.
        return None
    base: dict[str, Any] = {"source_text": text, "session_id": session_id}
    if isinstance(request, str):
        return {**base, "error": request}
    base.update(entity=request.entity, attribute=request.attribute, new_value=request.new_value)
    matches = [(r, p) for r in rows for p in parts(r["content"])
               if (p.entity, p.attribute) == (request.entity, request.attribute)]
    # A local override is the current value in its owning session.
    local_matches = [(r, p) for r, p in matches if r.get("is_override")]
    if local_matches:
        matches = local_matches
    if len(matches) != 1:
        return {**base, "error": "尚未更正：旧事实不能唯一可靠定位。请明确对象、属性及旧记忆原文；不覆盖不明的复合记录。"}
    row, part = matches[0]
    base.update(old_fact_id=row["fact_id"], old_content=row["content"], old_value=part.value,
                old_status=row["status"], old_scope=row["scope"], old_session_id=row["session_id"],
                scope="session" if request.local else row["scope"],
                start=part.start, end=part.end, is_override=bool(row.get("is_override")))
    if request.old_value is not None and request.old_value != part.value and request.new_value != part.value:
        return {**base, "error": "尚未更正：指定的旧值与当前版本不符。请核对当前值后再更正。"}
    base["new_content"] = row["content"][:part.start] + request.new_value + row["content"][part.end:]
    return base


def receipt_text(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    scope = "仅本次会话" if result["scope"] == "session" else "全局长期记忆"
    pending = "，仍为待确认" if result["old_status"] == "pending" else ""
    outcome = result["outcome"]
    if outcome == "unchanged":
        return f"当前{scope}中的{result['entity']}{result['attribute']}已是{result['new_value']}，未重复修改{pending}。"
    prefix = "该请求此前已处理，历史回执" if outcome == "replayed" else "已更正并读回核验"
    return (f"{prefix}：{result['entity']}{result['attribute']}，"
            f"{result['old_value']} → {result['new_value']}（{scope}{pending}）。其他内容保留。")
