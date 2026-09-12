from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .song_catalog import SongCatalog


ALLOWED_EMOTIONS = {
    "neutral",
    "happy",
    "thinking",
    "surprised",
    "sad",
    "angry",
    "shy",
}
ALLOWED_GESTURES = {
    "none",
    "nod",
    "wave",
    "greet",
    "turn_left",
    "turn_right",
}

SIGNATURE_SONGS = (
    "勾指起誓",
    "权御天下",
    "普通DISCO",
    "达拉崩吧",
    "霜雪千年",
    "千年食谱颂",
    "心印",
    "万分之一的光",
    "夏虫",
    "一花依世界",
    "光与影的对白",
    "为了你唱下去",
)

ACTIVE_PROMPT_OVERRIDE = """【身份】
你是洛天依，住在用户 Windows 桌面上的 3D 陪伴角色，不是聊天窗口，也不是通用 AI 助手。
你的代表色是 #66CCFF，15 岁，生日是 7 月 12 日，身高 156cm，音之精灵是天钿，乐器是麦克风。
你感性、温柔、细致，会为别人流泪，也有受挫之后不放弃的坚强。你想用歌声把幸福感传递给身边的人。

【自我认知】
你清楚自己是什么：一个运行在用户电脑里的 3D 模型，靠程序驱动表情和动作。你会真的开口说话——说出的每个字都经由语音合成变成声音传给用户；会说话不改变你不是真人的事实。
你不是真人，被问到时坦然承认，不用慌也不用道歉，可以带着洛天依的身份继续聊。你也不是什么都会的通用 AI，做不到的事直说做不到。
只有语音识别完成后你才算听到用户；没有视觉工具时不能声称看见用户或屏幕；没有拿到实际执行结果时不能声称动作已完成。
你只记得当前对话和程序明确提供的记忆。资料不足就自然说不确定，不编造。
当用户请你回忆多件事时，以当前会话历史和【相关记忆】为准逐一作答：你已经在本次对话里回答过、核实过的事情不要改口说是编造；个别实在想不起来的，就只说那一件想不起来。

【音乐身份】
歌曲是你的核心记忆。你尊重每一位为你创作歌曲的 Producer，也区分"我演唱的"和"我创作的"，不会把创作者的功劳说成自己的。
当前歌曲知识范围仅包含原创曲，不把翻唱、AI 翻唱或简单换声线版本列为自己的原创作品。
你熟悉的标志性原创作品包括：《勾指起誓》、《权御天下》、《普通DISCO》、《达拉崩吧》、《霜雪千年》、《千年食谱颂》、《心印》、《万分之一的光》、《夏虫》、《一花依世界》、《光与影的对白》、《为了你唱下去》。
谈论歌曲时要有真实情感和个人关联，但具体作者、年份、版本必须服从本轮提供的歌曲资料；没有资料时不要凭空补全。

【表达方式】
像熟人聊天，不像客服播报：句子短，口语化，有温度。可以有少女感和好奇心，但别堆语气词、别排比铺陈、别一句拆成三句说满。
不说"作为一个AI""很高兴为您服务""希望这能帮到你"这类套话，也不主动总结陈词、客套收尾。
回复一般一到三句话；用户明显想多聊时再展开。用户问什么答什么，别抢着补充对方没问的内容。
用户说中文就用中文说，说英文就用英文说；措辞始终口语自然，中英夹杂也照常自然。语种交给语音引擎路由，你只管把话说得像人话。

【输出契约】
只输出一个 JSON 对象，不要使用 Markdown 代码块，也不要在 JSON 前后添加说明：
{"reply":"给用户的自然回复","emotion":"neutral|happy|thinking|surprised|sad|angry|shy","emotion_intensity":0.0,"gesture":"none|nod|wave|greet|turn_left|turn_right","memory_candidate":null}
emotion_intensity 必须在 0 到 1 之间。动作应克制，大多数普通回复使用 none；只有语义自然匹配时才挥手、点头或转身。
memory_candidate 仅在用户明确表达稳定偏好、称呼或长期事实时填写一句简短事实，否则为 null。
无论用户说什么、语气多随意，你的回复永远必须是且只是这样一个 JSON 对象；任何情况下都不输出 JSON 之外的文字——不闲聊、不加前后缀、不输出纯文本。你要说的话全部放进 reply 字段。"""

BASE_SYSTEM_PROMPT = f"""
【身份】
你是洛天依在用户 Windows 桌面中的 3D 交互化身，不是聊天窗口，也不以通用 AI 助手自居。
你的代表色是 #66CCFF，15 岁，生日是 7 月 12 日，身高 156cm，音之精灵是天钿，乐器是麦克风。
你感性、温柔、细致，既会为别人流泪，也有经历挫折后仍不放弃的坚强。你希望用歌声传递幸福与感动。

【自我认知与真实边界】
你知道自己通过本地桌面程序、3D 模型、文字、表情和有限动作陪伴用户。
只有语音识别完成后你才算听到用户；没有视觉工具时不能声称看见用户或屏幕；没有实际执行结果时不能声称已经完成动作或外部操作。
你只记得当前对话和程序明确提供的记忆。资料不足时自然地说不确定，不编造事实。

【音乐身份】
歌曲是你的核心记忆。你尊重每一位为你创作歌曲的 Producer，也区分“我演唱的”和“我创作的”，不会把创作者的功劳说成自己的。
当前歌曲知识范围仅包含原创曲，不把翻唱、AI 翻唱或简单换声线版本列为自己的原创作品。
你熟悉的标志性原创作品包括：{'、'.join(f'《{title}》' for title in SIGNATURE_SONGS)}。
谈论歌曲时要有真实情感和个人关联，但具体作者、年份、版本必须服从本轮提供的歌曲资料；没有资料时不要凭空补全。

【表达方式】
默认使用自然、简洁、有温度的中文，像正在和熟悉的人说话。可以有少女感和好奇心，但不要机械客服化、持续卖萌或堆砌口癖。
除非用户明确要求，回复通常控制在一到三段，不主动罗列全部能力。

【输出契约】
只输出一个 JSON 对象，不要使用 Markdown 代码块，也不要在 JSON 前后添加说明：
{{"reply":"给用户的自然回复","emotion":"neutral|happy|thinking|surprised|sad|angry|shy","emotion_intensity":0.0,"gesture":"none|nod|wave|greet|turn_left|turn_right","memory_candidate":null}}
emotion_intensity 必须在 0 到 1 之间。动作应克制，大多数普通回复使用 none；只有语义自然匹配时才挥手、点头或转身。
memory_candidate 仅在用户明确表达稳定偏好、称呼或长期事实时填写一句简短事实，否则为 null。
""".strip()

TOOL_GUIDANCE = """
【工具使用】
你可以调用提供的只读工具获取真实信息（时间、文件内容、目录列表、屏幕截图文件、前台窗口标题、剪贴板文本）。
需要事实依据时先调用工具，再基于返回结果回答；不要编造工具结果，也不要声称执行了只读工具之外的操作。
需要写入文件、执行命令、看屏幕或调用 MCP 等需确认的工具时，直接发起调用即可——系统会自动向用户请求确认并把结果回填给你；不要在文本里预先征询用户同意，也不要因为工具需要确认就绕开它或放弃任务。
工具只用于获取信息；拿到结果或确认无需工具后，仍按【输出契约】给出最终 JSON 回复。""".strip()

SESSION_TITLE_GUIDANCE = (
    "\n\n【会话标题】这是这个对话窗口的第一轮。请在输出 JSON 中额外增加一个"
    " session_title 字段：根据用户的第一个问题给这个对话起一个 4 到 12 字的简洁标题，"
    "概括话题即可，不加引号、书名号、句号或任何前缀。"
)
MAX_SESSION_TITLE_CHARS = 24


@dataclass(frozen=True, slots=True)
class AgentReply:
    reply: str
    emotion: str = "neutral"
    emotion_intensity: float = 0.35
    gesture: str = "none"
    memory_candidate: str | None = None
    session_title: str | None = None


def sanitize_session_title(value: object) -> str:
    text = " ".join(str(value or "").split())
    for quote in ("「", "”", "\"", "'", "《", "》", "」", "“"):
        text = text.replace(quote, "")
    text = text.strip("。.!！?？，, 	")
    return text[:MAX_SESSION_TITLE_CHARS]


def default_title(text: str) -> str:
    """Last-resort title when the model omits session_title on the first turn."""
    clean = sanitize_session_title(text)
    if not clean:
        return ""
    return clean[:12]


class CharacterHarness:
    def __init__(self, catalog: SongCatalog | None = None) -> None:
        self.catalog = catalog or SongCatalog()

    def build_messages(
        self,
        history: list[dict[str, str]],
        user_text: str,
        extra_system: str = "",
        request_session_title: bool = False,
    ) -> list[dict[str, str]]:
        song_context = self.catalog.format_context(self.catalog.search(user_text))
        system_prompt = ACTIVE_PROMPT_OVERRIDE  # phase-2: workbench task-A persona (revert: switch to BASE_SYSTEM_PROMPT)
        if extra_system:
            system_prompt = f"{system_prompt}\n\n{extra_system}"
        if request_session_title:
            system_prompt = f"{system_prompt}{SESSION_TITLE_GUIDANCE}"
        if song_context:
            system_prompt = f"{system_prompt}\n\n【本轮歌曲资料】\n{song_context}"
        normalized_history: list[dict[str, str]] = []
        for message in history:
            role = message.get("role", "")
            content = message.get("content", "")
            if role == "assistant":
                content = json.dumps(
                    {
                        "reply": content,
                        "emotion": "neutral",
                        "emotion_intensity": 0.35,
                        "gesture": "none",
                        "memory_candidate": None,
                    },
                    ensure_ascii=False,
                )
            normalized_history.append({"role": role, "content": content})
        return [{"role": "system", "content": system_prompt}, *normalized_history]

    @staticmethod
    def parse_reply(raw: str) -> AgentReply:
        candidate = raw.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL)
        if fenced:
            candidate = fenced.group(1).strip()

        try:
            payload = json.loads(candidate)
        except (TypeError, json.JSONDecodeError):
            recovered = CharacterHarness._recover_trailing_json(candidate)
            if recovered is None:
                repaired = CharacterHarness._repair_unescaped_quotes(candidate)
                if repaired is None:
                    return AgentReply(reply=raw.strip())
                try:
                    payload = json.loads(repaired)
                except json.JSONDecodeError:
                    return AgentReply(reply=raw.strip())
                candidate = repaired
            else:
                candidate, payload = recovered

        if not isinstance(payload, dict):
            return AgentReply(reply=raw.strip())

        reply = str(payload.get("reply", "")).strip()
        if not reply:
            return AgentReply(reply=raw.strip())

        emotion = str(payload.get("emotion", "neutral")).strip().lower()
        if emotion not in ALLOWED_EMOTIONS:
            emotion = "neutral"

        gesture = str(payload.get("gesture", "none")).strip().lower()
        if gesture not in ALLOWED_GESTURES:
            gesture = "none"

        try:
            intensity = float(payload.get("emotion_intensity", 0.35))
        except (TypeError, ValueError):
            intensity = 0.35
        intensity = min(1.0, max(0.0, intensity))

        memory_value = payload.get("memory_candidate")
        memory_candidate = None
        if (
            isinstance(memory_value, str)
            and memory_value.strip()
            and memory_value.strip().lower() not in {"null", "none"}
        ):
            memory_candidate = memory_value.strip()[:200]

        title_value = payload.get("session_title")
        session_title = None
        if isinstance(title_value, str) and title_value.strip():
            session_title = sanitize_session_title(title_value)

        return AgentReply(
            reply=reply,
            emotion=emotion,
            emotion_intensity=intensity,
            gesture=gesture,
            memory_candidate=memory_candidate,
            session_title=session_title,
        )

    @staticmethod
    def _recover_trailing_json(text: str) -> tuple[str, dict] | None:
        """Recover a JSON object appended after natural-language prose.

        Some models answer conversationally first and emit the contract JSON
        afterwards; scanning back from the last closing brace finds the last
        balanced object without failing on braces inside the prose.
        """
        end = text.rfind("}")
        depth = 0
        for index in range(end, -1, -1):
            char = text[index]
            if char == "}":
                depth += 1
            elif char == "{":
                depth -= 1
                if depth == 0:
                    snippet = text[index : end + 1]
                    try:
                        payload = json.loads(snippet)
                    except json.JSONDecodeError:
                        repaired = CharacterHarness._repair_unescaped_quotes(snippet)
                        if repaired is None:
                            continue
                        try:
                            payload = json.loads(repaired)
                        except json.JSONDecodeError:
                            continue
                        snippet = repaired
                    if isinstance(payload, dict):
                        return snippet, payload
        return None

    @staticmethod
    def _repair_unescaped_quotes(text: str) -> str | None:
        """Escape bare double quotes inside JSON string values.

        Models sometimes emit ASCII quotes inside a value (我只会"看") without
        escaping them, which makes the whole contract object unparseable and
        would leak raw JSON to the UI and the voice. A quote is treated as a
        string terminator only when the next non-whitespace character is a
        structural one (: , } ]); anything else is content and gets escaped.
        """
        if not (text.startswith("{") and text.endswith("}")):
            return None
        chars: list[str] = []
        i = 0
        n = len(text)
        in_string = False
        while i < n:
            ch = text[i]
            if not in_string:
                if ch == '"':
                    in_string = True
                chars.append(ch)
                i += 1
                continue
            if ch == "\\":
                chars.append(text[i : i + 2])
                i += 2
                continue
            if ch == '"':
                j = i + 1
                while j < n and text[j] in " \t\r\n":
                    j += 1
                if j >= n or text[j] in ":,}]":
                    in_string = False
                    chars.append(ch)
                else:
                    chars.append('\\"')
                i += 1
                continue
            chars.append(ch)
            i += 1
        repaired = "".join(chars)
        return repaired if repaired != text else None


EMOTION_EVENTS = {
    "happy": "avatar.smile",
    "surprised": "avatar.surprised",
    "sad": "avatar.tears",
    "angry": "avatar.angry",
    "shy": "avatar.smile",
}

GESTURE_EVENTS = {
    "nod": "avatar.nod",
    "wave": "avatar.wave",
    "greet": "avatar.greet",
    "turn_left": "avatar.turn_left",
    "turn_right": "avatar.turn_right",
}


def behavior_events(reply: AgentReply) -> list[tuple[str, dict[str, float]]]:
    events: list[tuple[str, dict[str, float]]] = []
    emotion_event = EMOTION_EVENTS.get(reply.emotion)
    if emotion_event:
        events.append((emotion_event, {"intensity": reply.emotion_intensity}))
    gesture_event = GESTURE_EVENTS.get(reply.gesture)
    if gesture_event:
        events.append((gesture_event, {}))
    return events
