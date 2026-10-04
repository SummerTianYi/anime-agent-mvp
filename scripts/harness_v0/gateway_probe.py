"""Codex: two serialized, non-retrying gateway probes; never import production Core."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

from .prepare import dump, sha
from .runner import PACKAGE, verify
from .worker import sanitize

BATCH = PACKAGE / "batches/gateway-resume-01"


def credentials(env_file):
    from dotenv import dotenv_values
    values = dotenv_values(env_file)
    models = json.loads((PACKAGE / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))["models"]
    assert values.get("DEEPSEEK_API_KEY"), "Missing credential"
    assert values.get("GLM_CREDENTIAL_SOURCE") == "deepseek"
    for tag, name in (("ds", "DEEPSEEK_MODEL"), ("glm", "GLM_MODEL")):
        assert values.get(name) == models[tag]["model"], "Model differs from frozen baseline"
        assert values.get("DEEPSEEK_BASE_URL", "").rstrip("/") == models[tag]["base_url"]
    return values["DEEPSEEK_API_KEY"], models


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env-file", type=Path, required=True)
    p.add_argument("--output", type=Path, default=BATCH)
    args = p.parse_args()
    verify()
    key, models = credentials(args.env_file)
    output = args.output / "gateway-probes.json"
    assert not output.exists(), "Append-only: choose a new probe output directory"
    report = {"layer": "gateway-only/synthetic-text/no-core", "http_cap": 2,
              "parent_http_calls": 66, "cumulative_cap": 900, "probes": [],
              "script_sha256": sha(Path(__file__).read_bytes())}
    # Frozen auto policy is direct for exactly this domestic gateway.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for tag, config in models.items():
        if report["probes"]:
            time.sleep(2)
        body = {"model": config["model"], "stream": False,
                "messages": [{"role": "user", "content": "这是隔离连通性测试。请仅回复 GATEWAY_OK。"}]}
        req = urllib.request.Request(config["base_url"] + "/chat/completions",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        row = {"model_tag": tag, "model_configuration": config, "request_body": body,
               "started_utc": datetime.now(timezone.utc).isoformat(), "status": None, "http_calls": 1}
        start = time.monotonic()
        try:
            with opener.open(req, timeout=config["timeout_seconds"]) as response:
                row.update(status=response.status, response_body=json.loads(response.read()))
            message = row["response_body"]["choices"][0]["message"].get("content", "")
            row["passed"] = row["status"] == 200 and message.strip() == "GATEWAY_OK" and row["response_body"].get("model") == config["model"]
        except urllib.error.HTTPError as exc:
            row.update(status=exc.code, retry_after=exc.headers.get("Retry-After"),
                       error_body=exc.read(8192).decode("utf-8", errors="replace"), passed=False)
            exc.close()
        except Exception as exc:
            row.update(error_type=type(exc).__name__, passed=False)
        row["elapsed_ms"] = round((time.monotonic() - start) * 1000)
        report["probes"].append(sanitize(row, [], key))
        report["http_calls"] = len(report["probes"])
        report["all_passed"] = len(report["probes"]) == 2 and all(r["passed"] for r in report["probes"])
        dump(output, report)
        print(tag, "status", row["status"], "passed", row["passed"], "ms", row["elapsed_ms"], flush=True)
        if row["status"] in {401, 403, 429}:
            print("SHARED_GATEWAY_PAUSED", flush=True)
            break


if __name__ == "__main__":
    main()
