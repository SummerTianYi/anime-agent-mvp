"""Dispatch the existing write/confirm/read delivery hooks to narrow adapters."""
from . import email_task, file_task, issue_task
from .tool_contracts import tool_effect


def requested(text):
    return email_task.requested(text) or file_task.requests_file_delivery(text) or issue_task.requested(text)


def active(task):
    return bool(task.get("file_delivery") or "issue_contract" in task or "email_contract" in task)


def activate(task, text, *, edit=False):
    if email_task.requested(text) or (edit and "email_contract" in task):
        task["email_contract"] = email_task.contract(text, task.get("email_contract") if edit else None)
    elif issue_task.requested(text) or (edit and "issue_contract" in task):
        task["issue_contract"] = issue_task.contract(text, task.get("issue_contract") if edit else None)
    elif file_task.requests_file_delivery(text) or (edit and task.get("file_delivery")):
        task["file_delivery"] = True
        task["file_request_text"] = file_task.edited_file_request(task.get("file_request_text", ""), text) if edit else text


def guidance(task):
    if "email_contract" in task:
        return email_task.GUIDANCE
    return issue_task.GUIDANCE if "issue_contract" in task else file_task.FILE_TASK_GUIDANCE


def proposal_error(task, sid, name, args):
    if "email_contract" in task:
        return email_task.proposal_error(task, sid, name, args)
    if "issue_contract" in task:
        return issue_task.proposal_error(task, sid, name, args)
    if task.get("file_delivery") and name != "write_file" and tool_effect(name, args) != "read":
        return "当前文件任务不包含其他业务写入；该调用不能生成待办。只读调用仍须遵循原权限。"
    return file_task.literal_content_error(task.get("file_request_text", task["intent"]), name, args) if task.get("file_delivery") else ""


def completion_error(task, sid, actions, mode, **kwargs):
    adapter = email_task if "email_contract" in task else issue_task if "issue_contract" in task else file_task
    return adapter.completion_error(task, sid, actions, mode, **kwargs)


def render(task, sid, actions, fallback, **kwargs):
    renderer = email_task.render if "email_contract" in task else issue_task.render if "issue_contract" in task else file_task.render_file_delivery
    return renderer(task, sid, actions, fallback, **kwargs)


def after_actions(task, sid, actions, name, args):
    actions = list(actions)
    if "email_contract" in task:
        return []
    if "issue_contract" in task:
        return issue_task.after_actions(task, sid, actions, name, args)
    return [a["action_id"] for a in file_task.writes_for(task, sid, actions)
            if name == "read_file" and a["status"] == "succeeded"
            and file_task.same_path(args.get("path"), a["arguments"].get("path"))]
