"""Index named code objects in the supplied archive. No imported or executed reference modules."""
import argparse
import hashlib
import io
import json
import marshal
from pathlib import Path
from types import CodeType
from zipfile import ZipFile


def names(obj):
    yield obj.co_qualname
    for value in obj.co_consts:
        if isinstance(value,CodeType):
            yield from names(value)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    # Use only with the identified archive. Do not accept arbitrary serialized Python objects.
    with args.archive.open("rb") as src:
        digest=hashlib.file_digest(src,"sha256").hexdigest()
    if digest!="61e731f22c6a4c31bca91463506c0ac5a6f97075e0fa2d89ad95064107fd8a97":
        raise SystemExit("Reference archive fingerprint mismatch")
    result={"archive_sha256":digest,"bytecode":{}}
    with ZipFile(args.archive) as z:
        result["members"]=len(z.infolist())
        for stem in ("main","platform_core","agent_workflow"):
            data=z.read("Yachiyo/desktop-companion/backend/"+stem+".pyc")
            assert len(data)<3_000_000
            ns=names(marshal.loads(data[16:]))
            chosen=[n for n in ns if "<" not in n and
                    (n in {"AgentPlatform","EventBus","CardStore","ToolRegistry","set_reply","schedule_windows_reply",
                           "deliver_workflow_message","get_workflow_progress","cancel_workflow_task","add_conversation",
                           "generate_and_play_reply","process_batch_voice_turn","AgentPlatform.persona_prompt"} or
                     n.startswith("AgentWorkflow.") and any(w in n for w in ("start","cancel","progress","deliver")))]
            result["bytecode"][stem]={"sha256":hashlib.sha256(data).hexdigest(),"symbols":chosen}
        with ZipFile(io.BytesIO(z.read("Yachiyo/desktop-companion/latest-tablet.apk"))) as apk:
            result["android_classes11_dex_sha256"]=hashlib.sha256(apk.read("classes11.dex")).hexdigest()
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf8")
