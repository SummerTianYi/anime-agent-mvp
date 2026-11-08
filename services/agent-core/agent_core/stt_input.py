"""Manual-input lifecycle and local Traditional->Simplified conversion.

No network or TTS normalization. English, numbers and explicit literals are unchanged.
Windows NLS is built in (no model download or global dependency).
"""
import ctypes
import re
import sys
from dataclasses import dataclass

_LITERAL = re.compile(r'\x60\x60\x60[\s\S]*?\x60\x60\x60|\x60[^\x60]*\x60|https?://[^\s<>]+|[A-Za-z]:[\\/][^\s，。！？;；]+|(?:^|(?<=\s))/(?:[^\s，。！？;；]+)|"[^"]*"|「[^」]*」|“[^”]*”')


def _windows_simplify(text):
    if not text or not re.search(r"[\u3400-\u9fff]", text):
        return text
    if sys.platform != "win32":
        raise RuntimeError("本平台没有已安装的本地简体转换器")
    fn = ctypes.windll.kernel32.LCMapStringEx
    fn.argtypes = [ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_wchar_p,ctypes.c_int,
                   ctypes.c_wchar_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_longlong]
    fn.restype = ctypes.c_int
    size = fn("zh-CN",0x02000000,text,len(text),None,0,None,None,0)
    if size <= 0:
        raise RuntimeError("本地简体转换失败")
    buf = ctypes.create_unicode_buffer(size+1)
    if not fn("zh-CN",0x02000000,text,len(text),buf,size,None,None,0):
        raise RuntimeError("本地简体转换失败")
    return buf.value


def simplify_transcript(text, converter=_windows_simplify):
    output, last = [], 0
    for match in _LITERAL.finditer(text):
        output.extend((converter(text[last:match.start()]), match.group()))
        last = match.end()
    output.append(converter(text[last:]))
    return "".join(output)


@dataclass
class CaptureState:
    generation: int = 0
    capture_id: str = ""
    session_id: int | None = None
    owner: object = None
    phase: str = "idle"

    def invalidate(self):
        self.generation += 1
        self.capture_id = ""
        self.phase = "idle"

    def begin(self, capture_id, session_id, owner):
        self.invalidate()
        self.capture_id, self.session_id, self.owner = capture_id, session_id, owner
        self.phase = "recording"
        return self.generation

    def valid(self, generation):
        return generation == self.generation and bool(self.capture_id)
