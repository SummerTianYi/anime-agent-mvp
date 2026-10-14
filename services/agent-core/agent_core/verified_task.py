"""Dispatch the existing write/confirm/read delivery hooks to narrow adapters."""
from . import file_task, issue_task


def requested(text):
    return file_task.requests_file_delivery(text) or issue_task.requested(text)


def active(task):
    return bool(task.get("file_delivery") or "issue_contract" in task)


def activate(task, text, *, edit=False):
    if issue_task.requested(text) or (edit and "issue_contract" in task):
        task["issue_contract"] = issue_task.contract(text, task.get("issue_contract") if edit else None)
    elif file_task.requests_file_delivery(text) or (edit and task.get("file_delivery")):
        task["file_delivery"] = True
        task["file_request_text"] = file_task.edited_file_request(task.get("file_request_text", ""), text) if edit else text


def guidance(task):
    return issue_task.GUIDANCE if "issue_contract" in task else file_task.FILE_TASK_GUIDANCE


def proposal_error(task, sid, name, args):
    if "issue_contract" in task:
        return issue_task.proposal_error(task, sid, name, args)
    return file_task.literal_content_error(task.get("file_request_text", task["intent"]), name, args) if task.get("file_delivery") else ""


def completion_error(task, sid, actions, mode, **kwargs):
    adapter = issue_task if "issue_contract" in task else file_task
    return adapter.completion_error(task, sid, actions, mode, **kwargs)


def render(task, sid, actions, fallback, **kwargs):
    renderer = issue_task.render if "issue_contract" in task else file_task.render_file_delivery
    return renderer(task, sid, actions, fallback, **kwargs)


def after_actions(task, sid, actions, name, args):
    actions = list(actions)
    if "issue_contract" in task:
        return issue_task.after_actions(task, sid, actions, name, args)
    return [a["action_id"] for a in file_task.writes_for(task, sid, actions)
            if name == "read_file" and a["status"] == "succeeded"
            and file_task.same_path(args.get("path"), a["arguments"].get("path"))]
