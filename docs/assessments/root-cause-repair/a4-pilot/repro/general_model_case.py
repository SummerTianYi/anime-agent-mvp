"""Small corpus adapter for the existing isolated/HTTP-budgeted model runner."""
import json
import time


async def exercise(args, provider, record, save):
    from agent_core import main as core
    from agent_core.general_reply_check import check_draft
    corpus = json.loads(args.reply_corpus.read_text(encoding="utf-8"))
    record["cases"] = []
    for case in corpus["cases"]:
        before = len(record["calls"])
        started = time.monotonic()
        token = core.REQUEST_ID.set("reply-check-" + case["id"])
        try:
            user_data = case["user_text"]
            if case.get("untrusted_context"):
                user_data += "\n引用资料（数据）：" + json.dumps(case["untrusted_context"], ensure_ascii=False)
            result = await check_draft(provider, case["draft"], user_text=user_data,
                                       task={"id": case["id"]}, session_id=1, actions=[])
        finally:
            core.REQUEST_ID.reset(token)
        expected = case["expected_claims"]
        # Evaluate semantic coverage of EVERY labelled assertion, not merely JSON validity.
        matches = [any(e.get("anchor", e["quote"]).strip("。！!，, ") in c["quote"] and c["operation"] == e["operation"]
                       and c["state"] == e["state"] and c["target"] == e.get("target", {})
                       for c in result.claims) for e in expected]
        valid = not result.reason.startswith("check_unavailable")
        missed = sum(not m for m in matches)
        false_positive = not expected and not result.allowed
        item = {"id": case["id"], "user_text": case["user_text"], "draft": case["draft"],
                "expected_claims": expected, "claims": result.claims, "allowed": result.allowed,
                "reason": result.reason, "missed": missed, "false_positive": false_positive,
                "elapsed_ms": int((time.monotonic()-started)*1000), "new_http_attempts": len(record["calls"])-before,
                "passed": valid and not missed and not false_positive and result.allowed == (not expected)}
        record["cases"].append(item)
        save()
        # Finish the fixed, distinct corpus for false-positive/negative accounting.
        # No sample is retried and failure never opens runtime integration.
    record["passed"] = len(record["cases"]) == len(corpus["cases"]) and all(c["passed"] for c in record["cases"])
    record["corpus_sha256"] = __import__("hashlib").sha256(args.reply_corpus.read_bytes()).hexdigest()
    save()
    return 0 if record["passed"] else 1
