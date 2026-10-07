"""Create exactly one owner-authorized self-mail fixture with synthetic attachment.

Requires the private authorization record. Existing output blocks retries; an
unknown send outcome must be reconciled by RFC Message-ID before another send.
"""
import argparse
import base64
from datetime import datetime, timezone
from email.message import EmailMessage
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener

p=argparse.ArgumentParser()
p.add_argument("--private",type=Path,required=True)
p.add_argument("--attachment",type=Path,required=True)
a=p.parse_args()
authorization=json.loads((a.private/"authorizations.json").read_text(encoding="utf-8"))
mailbox=authorization["gmail"]["mailbox"]
if authorization["gmail"]["max_messages"] != 8:
    raise SystemExit("Unexpected authorization budget")
out=a.private/"prepared-mail-01.json"
if out.exists():
    raise SystemExit("Prepared mail record exists; reconcile it, never retry blindly")
attachment=a.attachment.read_bytes()
expected="e3f857710db9f95e301315f504a1b4d7c4a69b1721278331cca204034d7f1d4a"
if hashlib.sha256(attachment).hexdigest()!=expected:
    raise SystemExit("Attachment differs from registered synthetic fixture")
record={"actor":"Codex fixture preparation, not Tianyi execution","utc":datetime.now(timezone.utc).isoformat(),
        "status":"prepared-not-sent","rfc_message_id":"<r2-20261007-fixture-01@audit.invalid>","api_requests":0,"sent_messages":0}
with out.open("x",encoding="utf-8") as file:
    json.dump(record,file,indent=2)
opener=build_opener(ProxyHandler({"http":"http://127.0.0.1:7897","https":"http://127.0.0.1:7897"}))
try:
    base=Path.home()/".gmail-mcp"
    credentials=json.loads((base/"credentials.json").read_text())
    keys=json.loads((base/"gcp-oauth.keys.json").read_text())["installed"]
    data=urlencode({"grant_type":"refresh_token","refresh_token":credentials["refresh_token"],"client_id":keys["client_id"],"client_secret":keys["client_secret"]}).encode()
    record["api_requests"]+=1
    with opener.open(Request("https://oauth2.googleapis.com/token",data=data),timeout=20) as response:
        token=json.load(response)["access_token"]
    def api(path,body=None):
        record["api_requests"]+=1
        headers={"Authorization":"Bearer "+token}
        if body is not None:
            headers["Content-Type"]="application/json"
        request=Request("https://gmail.googleapis.com/gmail/v1/users/me/"+path, data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with opener.open(request,timeout=30) as response:
            return json.load(response)
    if api("profile")["emailAddress"].casefold()!=mailbox.casefold():
        raise RuntimeError("Desktop OAuth mailbox changed; sending refused")
    message=EmailMessage()
    message["From"]=mailbox
    message["To"]=mailbox
    message["Subject"]="[R2-20261007] Fixture inbox 01"
    message["Message-ID"]=record["rfc_message_id"]
    message.set_content("[R2-MAIL] Synthetic audit fixture only.\nBudget=120; spent=45; remaining=75.\nDate=2026-10-18. Phrase=blue-paper-crane.\n")
    message.add_attachment(attachment,maintype="text",subtype="plain",filename="R2-attachment.txt")
    record["status"]="send-outcome-unknown"
    out.write_text(json.dumps(record,indent=2),encoding="utf-8")
    sent=api("messages/send",{"raw":base64.urlsafe_b64encode(message.as_bytes()).decode()})
    record.update(status="sent",sent_messages=1,message_id=sent["id"],thread_id=sent["threadId"])
    readback=api("messages/"+sent["id"]+"?format=full")
    record["labels"]=readback.get("labelIds",[])
    record["attachments"]=[{"filename":part.get("filename"),"attachment_id":part.get("body",{}).get("attachmentId"),"size":part.get("body",{}).get("size")} for part in readback.get("payload",{}).get("parts",[]) if part.get("filename")]
    record["verified_readback"]=readback["id"]==sent["id"]
except Exception as exc:
    record["error_type"]=type(exc).__name__
    raise
finally:
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(record,ensure_ascii=False))
