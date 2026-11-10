"""Verified tool semantics shared by permission checks and receipt delivery.

These classifications never grant permission. Unknown tools remain conservative;
an advertised tool name alone is not proof that an operation is read-only.
"""
from __future__ import annotations
import re

METHOD_EFFECTS = {
    "mcp__github__issue_write": {"create": "write", "update": "write"},
    "mcp__github__sub_issue_write": {"add": "write", "remove": "write", "reprioritize": "write"},
    "mcp__github__issue_read": dict.fromkeys(("get", "get_comments", "get_sub_issues", "get_parent", "get_labels"), "read"),
    "mcp__github__pull_request_read": dict.fromkeys(("get", "get_diff", "get_status", "get_files", "get_commits",
        "get_review_comments", "get_reviews", "get_comments", "get_check_runs"), "read"),
    "mcp__github__pull_request_review_write": dict.fromkeys(("create", "submit_pending", "delete_pending", "resolve_thread", "unresolve_thread"), "write"),
}
READ_TOOLS = frozenset({
    "get_time", "read_file", "list_dir", "screenshot", "active_window", "clipboard_read", "public_web_search",
    "look_at_screen", "recall_memory", "read_tool_result",
    "mcp__gmail__search_emails", "mcp__gmail__read_email", "mcp__gmail__list_email_labels",
    "mcp__gmail__list_filters", "mcp__gmail__get_filter", "mcp__drive__search",
    "mcp__search__tavily_search", "mcp__search__tavily_extract", "mcp__search__tavily_crawl",
    "mcp__search__tavily_map", "mcp__search__tavily_research",
})
# Verified readOnlyHint entries in the captured deployed schema; no name-prefix
# heuristic. Downloading an attachment writes a local file and stays non-read.
READ_TOOLS |= frozenset("mcp__github__" + name for name in (
    "get_commit", "get_file_contents", "get_label", "get_latest_release", "get_me", "get_release_by_tag",
    "get_tag", "get_team_members", "get_teams", "list_branches", "list_commits", "list_issue_fields",
    "list_issue_types", "list_issues", "list_pull_requests", "list_releases", "list_repository_collaborators",
    "list_tags", "search_code", "search_commits", "search_issues", "search_pull_requests", "search_repositories", "search_users"))
READ_TOOLS |= frozenset("mcp__browser__" + name for name in (
    "browser_console_messages", "browser_find", "browser_network_requests", "browser_network_request",
    "browser_take_screenshot", "browser_snapshot", "browser_wait_for"))
GMAIL_ERROR_TOOLS = frozenset({
    "read_email", "send_email", "draft_email", "search_emails", "modify_email", "delete_email",
    "list_email_labels", "create_label", "update_label", "delete_label", "get_or_create_label",
    "batch_modify_emails", "batch_delete_emails", "download_attachment",
    "create_filter", "list_filters", "get_filter", "delete_filter", "create_filter_from_template",
})
# Observed connector exception messages, not a search for 'error' in user data.
GMAIL_ERROR_MESSAGES = frozenset({"Invalid id value", "Requested entity was not found.", "invalid_grant"})


def invalid_method(tool: str, arguments: dict) -> bool:
    methods = METHOD_EFFECTS.get(tool)
    method = arguments.get("method")
    return methods is not None and (not isinstance(method, str) or method not in methods)


def tool_effect(tool: str, arguments: dict) -> str:
    if tool in METHOD_EFFECTS:
        method = arguments.get("method")
        return METHOD_EFFECTS[tool].get(method, "unknown") if isinstance(method, str) else "unknown"
    if tool in READ_TOOLS:
        return "read"
    # Conservative delivery for unclassified tools; this does not change ASK.
    return "write" if tool in {"write_file", "run_command"} else "unknown"


def gmail_send_id(raw: dict):
    """Native 1.1.11 success envelope, never an ID found in model/user text."""
    content = raw.get("content", [])
    if raw.get("isError") is True or "structuredContent" in raw or len(content) != 1 or content[0].get("type") != "text":
        return None
    match = re.fullmatch(r"Email sent successfully with ID: ([A-Za-z0-9_-]+)", content[0].get("text", ""))
    return match[1] if match and match[1].lower() not in {"undefined", "null", "none"} else None


def normalize_mcp_result(server: str, tool: str, raw: dict, text: str) -> dict:
    failed = raw.get("isError") is True
    outcome = "failed" if failed else "succeeded"
    kind = "business_error" if failed else "success"
    content = raw.get("content", [])
    if (server == "gmail" and tool in GMAIL_ERROR_TOOLS and len(content) == 1
            and content[0].get("type") == "text" and "structuredContent" not in raw
            and (text.startswith("Error: ") or (tool == "download_attachment"
                 and text.startswith("Failed to download attachment: ")))):
        # @gongrzhe/server-gmail-autoauth-mcp 1.1.11 wraps each successful read
        # in fixed headers. Only its entire error envelope starts with Error:.
        failed = True
        message = text.removeprefix("Error: ")
        outcome = "failed" if tool_effect("mcp__gmail__" + tool, {}) == "read" or message in GMAIL_ERROR_MESSAGES else "unknown"
        kind = "business_error" if outcome == "failed" else "unconfirmed_error"
    if server == "gmail" and tool in {"batch_modify_emails", "batch_delete_emails"}:
        batch = re.match(r"Batch (?:label modification|delete operation) complete\.\nSuccessfully (?:processed|deleted): (\d+) messages\nFailed to (?:process|delete): ([1-9]\d*) messages\n", text)
        if batch:
            failed = True
            # The connector retries failed Promise.all batches item-by-item;
            # even a zero success count cannot disprove earlier side effects.
            outcome = "unknown"
            kind = "partial" if int(batch[1]) else "unconfirmed_error"
    if not failed and server == "gmail" and tool == "send_email" and not gmail_send_id(raw):
        # Dispatch may have succeeded. An absent/unrecognized ID is not a
        # negative acknowledgment and must retain the no-retry UNKNOWN guard.
        failed, outcome, kind = True, "unknown", "unconfirmed_receipt"
    empty = not failed and server == "gmail" and tool == "search_emails" and not text.strip()
    return {"ok": not failed, "outcome": outcome,
            "result_kind": "empty" if empty else kind,
            "text": "查询成功，没有匹配的邮件（0 条）。" if empty else text,
            "raw_result": raw, **({"error": text or "连接器报告业务失败"} if failed else {})}
