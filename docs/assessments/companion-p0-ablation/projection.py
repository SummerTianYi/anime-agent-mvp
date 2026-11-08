"""Turn-local experiment over the *already admitted* companion history. No I/O or task state."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re

# Keep offsets into the actual utterance while excluding quoted/dependent speech from control cues.
QUOTES = re.compile(r'“[^”]*”|「[^」]*」|『[^』]*』|‘[^’]*’|"[^"]*"|《[^》]*》')
CLAUSE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;\n]*|[。！？!?；;\n]+")
OFFER = re.compile(r"要不要|不如|要不(?!是)|你可以|我们可以|咱们可以|可以先|建议你|"
                   r"(?:我帮你|一起).{0,20}(?:好不好|好吗|吧|[？?])|你(?:先|再).{1,30}(?:看看|试试|吧|呢)")
ASK = re.compile(r"(?:吗|么|哪|多久|几个|几次|什么|还是|(?:会|能|有|要)不(?:会|能|有|要)).{0,45}[？?]|"
                 r"我(?:有点|还|挺)?好奇|(?:告诉我|跟我说说|讲给我听)|[？?]\s*$")
REFUSE = re.compile(r"不(?:想|用|必|要|需要)(?:再|听|你|给我|帮我|替我|讲|说|谈|问|试|准备|了)|"
                    r"(?:先|暂时)?别(?:再|教|让|讲|说|问|给|替|帮|追)|"
                    r"(?:先)?让我(?:缓|歇)|改天再(?:说|聊|试)|先放一放|先搁一搁|不急着(?:想|练|改)")
ACCEPT = re.compile(r"(?:就|那就)?按你(?:说|提|建议)的|我(?:愿意|决定)试|那就试试|"
                    r"^(?:好啊|好呀|行啊|可以呀|可以|行|好)[。！!\s]*$")
HELP = re.compile(r"怎么(?:说|办|做|写|弄|分|开|选|接|改|回|念)|如何|帮我|给我.{0,12}(?:句|个|点|些)|"
                  r"能不能|能.{0,12}(?:举|给|讲)|想请教|指什么|有何区别|你想先知道")
BACK = re.compile(r"(?:回到|接着|接回|说回|重新聊|再聊聊|刚才(?:说|聊|提)的|之前(?:说|聊|提)的)")
PLAY = re.compile(r"给你(?:颁|发个奖)|封你|颁给你|算你赢|逗你的|哈哈|"
                  r"(?:好[，, ]*){2,}.{0,22}(?:借你|归你|送你)|你(?:可真|真是|挺|真|很|太|也太).{0,12}(?:会|厉害|懂|棒|有意思)")
SHARE = re.compile(r"只是想(?:说|分享|讲)|我(?:刚|看|发现|听|今天|终于|还是|觉得|有点)|"
                   r"刚(?:刚|才)|路上|路口|窗外|今天|正好|刚好|结果|居然|原来")
ANAPHORA = re.compile(r"^(?:第[一二三两\d]+(?:个|种|条)|前者|后者|就是(?:这|那)个|你说的(?:这|那)个)")
REPORTED = re.compile(r"(?:他|她|别人|台词|原文|例句|引用|反话|才怪|讽刺).{0,8}(?:说|是|写|叫|[：:])|反话|才怪")
GLOBAL_NO = re.compile(r"别.{0,7}(?:问|教|建议|支招)|不想听建议|不用.{0,6}(?:建议|支招)")
GENERIC = {"刚才", "之前", "现在", "好像", "可以", "一下", "这个", "那个", "你说", "说的",
           "给我", "帮我", "我想", "我们", "要不", "不要", "不想", "一个", "真的", "准备", "还是",
           "一起", "要不要", "就是", "说说", "想想", "今天", "时候"}


def masked(text):
    return QUOTES.sub(lambda m: " " * len(m.group()), text)


def grams(text):
    return {s[i:i + 2] for s in re.findall(r"[\u3400-\u9fff]+|[A-Za-z0-9]+", text.lower())
            for i in range(len(s) - 1)} - GENERIC


@dataclass
class Proposal:
    message: int  # one-based among chronological non-system messages
    start: int
    end: int
    kind: str
    status: str = "未确认"
    evidence: int | None = None
    cue: str = ""


def find_proposals(index, body):
    clean = masked(body)
    for part in CLAUSE.finditer(clean):
        clause = part.group()
        if not clause.strip() or REPORTED.search(clause):
            continue
        kind = "建议" if OFFER.search(clause) else "询问" if ASK.search(clause) else None
        if kind:
            yield Proposal(index, part.start(), part.end(), kind)


def register_stance(index, body, history, proposals):
    clean = masked(body).strip()
    if REPORTED.search(clean):
        return
    reject = REFUSE.search(clean)
    accept = ACCEPT.search(clean)
    if not (reject or accept):
        return
    # An explicit later request can start a fresh goal; it doesn't rewrite an earlier rejection.
    eligible = [p for p in proposals if p.status == "未确认"]
    if not eligible:
        return
    at_hand = [p for p in eligible if p.message == index - 1]
    if reject and GLOBAL_NO.search(clean):
        targets = at_hand
    else:
        evidence = grams(clean)
        scored = [(len(evidence & grams(history[p.message-1]["content"][p.start:p.end])), p)
                  for p in eligible]
        best = max(n for n, _ in scored)
        winners = [p for n, p in scored if n == best]
        # A non-adjacent item needs an explicit backward reference. Ambiguous assent stays open.
        if best and len(winners) == 1 and (winners[0] in at_hand or BACK.search(clean)):
            targets = winners
        else:
            targets = at_hand if len(at_hand) == 1 and not best else []
    cue = reject or accept
    for proposal in targets:
        proposal.status = "明确拒绝" if reject else "明确接受"
        proposal.evidence, proposal.cue = index, cue.group()


def current_act(history):
    text = masked(history[-1]["content"]).strip()
    for pattern, label in ((REPORTED, "引用或反讽"), (HELP, "求助"), (REFUSE, "拒绝"),
                           (BACK, "恢复话题"), (ACCEPT, "接纳"), (ANAPHORA, "承接"),
                           (PLAY, "赞许或玩笑"), (SHARE, "分享")):
        for match in pattern.finditer(text):
            prefix = re.split(r"[，,。；;！？!?\n]", text[:match.start()])[-1]
            if pattern is HELP and (REFUSE.search(prefix) or re.search(r"别|不(?:要|必|用|想)$", prefix)):
                # Scope a negative to its own clause. A constraint can coexist with a request.
                continue
            if pattern is HELP and BACK.search(text):
                label = "恢复并求助"
            return label, match.group()
    return "不确定", ""


def project(history, variant):
    """Return the data index and optional demotions. The caller preserves user messages verbatim."""
    if variant not in ("B", "C") or not history or history[-1]["role"] != "user":
        raise ValueError("Expected companion B/C history ending at the current user")
    proposals = []
    for i, message in enumerate(history, 1):
        if message["role"] == "assistant":
            proposals.extend(find_proposals(i, message["content"]))
        elif message["role"] == "user":
            register_stance(i, message["content"], history, proposals)
        else:
            raise ValueError("Unexpected non-companion role")
    state = {"proposals": [asdict(p) for p in proposals]}
    # Only host-generated labels, indices and offsets enter system authority. Raw dialogue stays in role.
    lines = [f"消息{p.message} 助手{p.kind}[{p.start}:{p.end}] {p.status}"
             + (f"（用户消息{p.evidence}）" if p.evidence else "") for p in proposals]
    note = "【本轮对话索引·消息从1起，区间为字符位置】\n" + "\n".join(lines) if lines else ""
    demote = {}
    if variant == "C":
        act, cue = current_act(history)
        overlap = grams(masked(history[-1]["content"]))
        related = [i for i, message in enumerate(history[:-1], 1) if overlap & grams(masked(message["content"]))]
        # For explicit returns / references, keep the complete chronological replies in focus.
        if act in {"赞许或玩笑", "拒绝", "分享"}:
            for p in proposals:
                span = history[p.message-1]["content"][p.start:p.end]
                if p.status != "明确接受" and (act != "分享" or not overlap & grams(span)):
                    demote.setdefault(p.message, []).append((p.start, p.end))
        state.update(act=act, act_cue=cue, related=related, background=demote)
        note += ("\n" if note else "") + f"当前交流：{act}。词面相关历史消息：{related}。"
    return state, note, demote


def background_messages(messages, demote):
    """Rehouse only inactive clauses under their original assistant role; all characters survive."""
    for index, spans in demote.items():
        packet = json.loads(messages[index]["content"])
        original = packet["reply"]
        parts, remainder = [], []
        last = 0
        for start, end in spans:
            remainder.append(original[last:start])
            parts.append(original[start:end])
            last = end
        packet["reply"] = "".join([*remainder, original[last:]])
        messages[index] = {**messages[index], "content": json.dumps(
            {"过往助手提议（背景）": parts, **packet}, ensure_ascii=False)}
