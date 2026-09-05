"""Chinese-friendly lexical memory retrieval (zcode, phase B 记忆接入).

Ported from the anime-agent-workbench Task B implementation. Function
characters are stripped, text is tokenized into characters and character
bigrams, tokens are weighted by smoothed IDF over the candidate set, and
abstract attribute nouns in the query (职业/爱好/颜色/城市/宠物/生日/称呼)
are expanded into low-weight concrete indicator words. This bridges pairs
like "用户的职业" -> "用户是后端工程师" that share no lexical token.
"""

from __future__ import annotations

import math

_STOP_CHARS = set("的了是在最了为对吗呢吧啊嘛哦什哪怎谁用户您请很也还又都就")

_EXPANSION = {
    "颜色": "蓝 红 绿 黄 白 黑 紫 粉 棕 灰 颜色",
    "生日": "出生 生日 诞辰 岁 蛋糕 星座",
    "称呼": "叫 名字 姓名 昵称 称谓 称呼",
    "职业": "工程师 程序 上班 工作 公司 加班 同事 设计师 医生 老师 后端 前端",
    "爱好": "喜欢 兴趣 周末 游戏 唱歌 画画 旅游 徒步 健身 运动 休闲",
    "宠物": "猫 狗 鸟 鱼 养 宠物",
    "城市": "工作 住 生活 地址 位置 城市",
}

_EXPANSION_WEIGHT = 0.4
_UNIGRAM_WEIGHT = 0.5
_RELATED_RATIO = 0.5


def _content_chars(text: str) -> list[str]:
    return [c for c in text if c not in _STOP_CHARS and not c.isspace()]


def _tokens(text: str) -> tuple[set[str], set[str]]:
    chars = _content_chars(text)
    return set(chars), {a + b for a, b in zip(chars, chars[1:])}


def _query_parts(query: str) -> tuple[set[str], set[str], set[str], set[str]]:
    q_uni, q_bi = _tokens(query)
    exp_uni: set[str] = set()
    exp_bi: set[str] = set()
    for key, indicators in _EXPANSION.items():
        if key in query:
            for word in indicators.split():
                w_uni, w_bi = _tokens(word)
                exp_uni |= w_uni
                exp_bi |= w_bi
    return q_uni, q_bi, exp_uni, exp_bi


def retrieve_relevant(query: str, stored: list[str], limit: int = 3) -> list[str]:
    """Rank candidate memories against a query; returns the relevant subset.

    Facts scoring at least half of the best score are returned (usually the
    single best match). With zero lexical signal the first fact is returned
    deterministically so an empty recall never looks like an error.
    """
    if not stored:
        return []
    q_uni, q_bi, q_exp_uni, q_exp_bi = _query_parts(query)
    fact_uni: list[set[str]] = []
    fact_bi: list[set[str]] = []
    for fact in stored:
        fu, fb = _tokens(fact)
        fact_uni.append(fu)
        fact_bi.append(fb)

    df_uni: dict[str, int] = {}
    df_bi: dict[str, int] = {}
    for fu in fact_uni:
        for token in fu:
            df_uni[token] = df_uni.get(token, 0) + 1
    for fb in fact_bi:
        for token in fb:
            df_bi[token] = df_bi.get(token, 0) + 1
    n = len(stored)
    idf_u = {t: math.log((n + 1) / (d + 0.5)) for t, d in df_uni.items()}
    idf_b = {t: math.log((n + 1) / (d + 0.5)) for t, d in df_bi.items()}

    scores: list[tuple[float, int]] = []
    for i, _fact in enumerate(stored):
        score = 0.0
        for token in q_uni & fact_uni[i]:
            score += idf_u.get(token, 0.0) * _UNIGRAM_WEIGHT
        for token in q_bi & fact_bi[i]:
            score += idf_b.get(token, 0.0)
        for token in q_exp_uni & fact_uni[i]:
            score += idf_u.get(token, 0.0) * _UNIGRAM_WEIGHT * _EXPANSION_WEIGHT
        for token in q_exp_bi & fact_bi[i]:
            score += idf_b.get(token, 0.0) * _EXPANSION_WEIGHT
        scores.append((score, i))

    best = max(score for score, _ in scores)
    if best <= 0.0:
        return [stored[0]]
    picked = [
        stored[i]
        for score, i in sorted(scores, key=lambda pair: (-pair[0], pair[1]))
        if score >= best * _RELATED_RATIO
    ]
    return picked[:limit]


def score_retrieval(golden: list[dict]) -> dict[str, float] | None:
    """Micro-averaged precision/recall of retrieve_relevant over a golden set."""
    if not golden:
        return None
    hits = retrieved_total = relevant_total = 0
    for item in golden:
        relevant = set(item.get("relevant", []))
        got = set(retrieve_relevant(str(item.get("query", "")), [str(f) for f in item.get("stored", [])]))
        hits += len(got & relevant)
        retrieved_total += len(got)
        relevant_total += len(relevant)
    return {
        "precision": hits / retrieved_total if retrieved_total else 0.0,
        "recall": hits / relevant_total if relevant_total else 0.0,
    }
