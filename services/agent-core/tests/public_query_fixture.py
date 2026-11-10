"""Script native model proposals for delivery tests. No fallback implementation of user intent."""
from unittest.mock import patch
from agent_core import main as core, public_query_turn as query, public_search


def native(arguments):
    return {"content":"","tool_calls":[{"id":"fixture-turn","name":query.NAME,"arguments":arguments}]}


def lookup(subject="F1", fields=("积分榜",), **extra):
    return {"mode":"lookup", "subject":subject, "fields":list(fields), **extra}


def script(test, *proposals):
    upcoming = iter(proposals)
    async def respond(messages, tools):
        if tools != [query.SCHEMA]:
            return {"content":'{"reply":"隔离测试回复。"}', "tool_calls":[]}
        args = dict(next(upcoming,lookup()))
        if args.get("mode") in {"lookup","replace"}:
            original = messages[-1]["content"]
            args.setdefault("evidence", public_search.answer_question(original).strip())
        return native(args)
    mock = patch.object(core.provider,"complete_with_tools",side_effect=respond,create=True)
    result = mock.start()
    test.addCleanup(mock.stop)
    return result
