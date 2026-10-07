"""Read desktop OAuth account identity, never print/store credential values."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener
from urllib.error import HTTPError

p = argparse.ArgumentParser()
p.add_argument("--production", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    raise SystemExit("Evidence exists; no overwrite")
opener = build_opener(ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
base = Path.home() / ".gmail-mcp"
results = {"utc": datetime.now(timezone.utc).isoformat(), "actor": "Codex read-only account preflight, not Tianyi execution", "requests": 0}
for service, cred_name, keyfile, url in (
    ("gmail", "credentials.json", base / "gcp-oauth.keys.json", "https://gmail.googleapis.com/gmail/v1/users/me/profile"),
    ("drive", "gdrive-credentials.json", a.production / "gcp-oauth.keys.json", "https://www.googleapis.com/drive/v3/about?fields=user(emailAddress,permissionId)"),
):
    try:
        credentials = json.loads((base / cred_name).read_text(encoding="utf-8"))
        keys = json.loads(keyfile.read_text(encoding="utf-8"))
        config = keys.get("installed", keys.get("web", {}))
        form = urlencode({"grant_type": "refresh_token", "refresh_token": credentials["refresh_token"],
                          "client_id": config["client_id"], "client_secret": config["client_secret"]}).encode()
        results["requests"] += 1
        with opener.open(Request("https://oauth2.googleapis.com/token", data=form), timeout=20) as response:
            token = json.load(response)["access_token"]
        results["requests"] += 1
        with opener.open(Request(url, headers={"Authorization": "Bearer " + token}), timeout=20) as response:
            profile = json.load(response)
        user = profile if service == "gmail" else profile["user"]
        results[service] = {"ok": True, "email": user["emailAddress"], "scope": credentials.get("scope", "")}
    except HTTPError as exc:
        try:
            body = json.loads(exc.read())
            error = body.get("error")
            code = error.get("status", "api_error") if isinstance(error, dict) else str(error)
        except Exception:
            code = "unparsed_error"
        results[service] = {"ok": False, "status": exc.code, "error_code": code}
    except Exception as exc:
        results[service] = {"ok": False, "error_type": type(exc).__name__}
a.output.parent.mkdir(parents=True, exist_ok=True)
with a.output.open("x", encoding="utf-8") as output:
    json.dump(results, output, ensure_ascii=False, indent=2)
print(json.dumps(results, ensure_ascii=False))
