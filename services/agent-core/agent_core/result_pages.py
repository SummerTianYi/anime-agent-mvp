"""Bounded, session-local continuation of already-authorized tool results."""
import json
import uuid

PAGE_CHARS = 2000
MAX_CACHE_CHARS = 4 * 1024 * 1024
SCHEMA = {"type":"function","function":{"name":"read_tool_result",
    "description":"续取本任务已授权工具长结果。ref来自回执，offset为字符位置；可用total_chars-2000读取末尾。只返回缓存数据，不读取新文件或外部服务。",
    "parameters":{"type":"object","properties":{"ref":{"type":"string"},"offset":{"type":"integer","minimum":0}},
                  "required":["ref","offset"],"additionalProperties":False}}}


class ResultPages:
    def __init__(self):
        self.items = {}
        self.size = 0

    def pack(self, result):
        raw = json.dumps(result, ensure_ascii=False, default=str)
        if len(raw) <= PAGE_CHARS:
            return result
        if len(raw) > MAX_CACHE_CHARS:
            return {"ok":False,"error":"结果超出4Mi字符缓存上限，请缩小查询；正文未完整载入",
                    "outcome":result.get("outcome","result_too_large")}
        while self.items and self.size + len(raw) > MAX_CACHE_CHARS:
            key = next(iter(self.items)); self.size -= len(self.items.pop(key))
        ref = uuid.uuid4().hex
        self.items[ref] = raw
        self.size += len(raw)
        return {**{k:v for k,v in result.items() if k in ("ok","outcome","action_id","revision","args_hash","error")},
                **self.read(ref,0), "instruction":"内容未读完。用read_tool_result及ref/offset续取；total_chars是完整长度。"}

    def read(self, ref, offset=0):
        if ref not in self.items:
            return {"ok":False,"error":"引用不属于当前任务或已过期；不能跨会话读取"}
        raw = self.items[ref]
        if type(offset) is not int or offset < 0 or offset > len(raw):
            return {"ok":False,"error":"offset必须是正文范围内非负整数"}
        end = min(len(raw),offset+PAGE_CHARS)
        return {"content":raw[offset:end], "ref":ref, "offset":offset, "total_chars":len(raw),
                "next_offset":end if end < len(raw) else None, "truncated":end < len(raw)}
