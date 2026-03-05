#!/usr/bin/env python3
"""Validate optional external API credentials from local .env."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable


DEFAULT_ENV = ".env"
DEFAULT_TIMEOUT_S = 20
DEFAULT_USER_AGENT = (
    "fdml-core-api-check/1.0 (+https://github.com/ShivsaranshThakur1-Coder/fdml-core)"
)


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def env_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def fetch(
    url: str,
    *,
    timeout_s: int,
    user_agent: str,
    headers: dict[str, str] | None = None,
) -> tuple[int | None, str]:
    merged = {"User-Agent": user_agent, "Accept": "application/json,text/plain;q=0.9,*/*;q=0.1"}
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, headers=merged, method="GET")
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=timeout_s) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def check_groq(key: str, timeout_s: int, user_agent: str) -> tuple[bool, str]:
    status, body = fetch(
        "https://api.groq.com/openai/v1/models",
        timeout_s=timeout_s,
        user_agent=user_agent,
        headers={"Authorization": f"Bearer {key}"},
    )
    if status == 200:
        try:
            payload = json.loads(body)
        except Exception:  # noqa: BLE001
            return False, "invalid_json_response"
        count = len(payload.get("data", [])) if isinstance(payload, dict) else 0
        return True, f"ok models={count}"
    if status == 403 and "cloudflare" in body.lower():
        return False, "forbidden_cloudflare_block"
    return False, f"http_{status}" if status is not None else body


def check_ocr_space(key: str, timeout_s: int, user_agent: str) -> tuple[bool, str]:
    image_url = "https://ocr.space/Content/Images/receipt-ocr-original.jpg"
    url = (
        "https://api.ocr.space/parse/imageurl?apikey="
        + urllib.parse.quote(key)
        + "&url="
        + urllib.parse.quote(image_url)
    )
    status, body = fetch(url, timeout_s=timeout_s, user_agent=user_agent)
    if status == 200 and ('"OCRExitCode":1' in body or "ParsedResults" in body):
        return True, "ok"
    return False, f"http_{status}" if status is not None else body


def check_deepl(key: str, timeout_s: int, user_agent: str) -> tuple[bool, str]:
    status, body = fetch(
        "https://api-free.deepl.com/v2/usage",
        timeout_s=timeout_s,
        user_agent=user_agent,
        headers={"Authorization": f"DeepL-Auth-Key {key}"},
    )
    if status == 200 and "character_count" in body:
        return True, "ok"
    return False, f"http_{status}" if status is not None else body


def check_youtube(key: str, timeout_s: int, user_agent: str) -> tuple[bool, str]:
    query = urllib.parse.urlencode(
        {"part": "snippet", "q": "folk dance", "maxResults": "1", "type": "video", "key": key}
    )
    status, body = fetch(
        "https://www.googleapis.com/youtube/v3/search?" + query,
        timeout_s=timeout_s,
        user_agent=user_agent,
    )
    if status == 200 and '"items"' in body:
        return True, "ok"
    return False, f"http_{status}" if status is not None else body


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Check external API keys configured in .env.")
    ap.add_argument("--env-file", default=DEFAULT_ENV, help="path to local env file")
    ap.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S, help="HTTP timeout seconds")
    ap.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP user agent")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    env = load_env(Path(args.env_file))
    if not env:
        print(f"FAIL: env file missing or empty: {args.env_file}")
        return 2

    if env_truthy(env.get("FDML_OFFLINE", "0")):
        print("SKIP: FDML_OFFLINE=1 (network checks disabled)")
        return 0

    checks: list[tuple[str, str, Callable[[str, int, str], tuple[bool, str]]]] = [
        ("groq", "GROQ_API_KEY", check_groq),
        ("ocr_space", "OCR_SPACE_API_KEY", check_ocr_space),
        ("deepl", "DEEPL_API_KEY", check_deepl),
        ("youtube", "YOUTUBE_API_KEY", check_youtube),
    ]

    failures: list[str] = []
    checked = 0
    for label, key_name, fn in checks:
        key = env.get(key_name, "")
        if not key:
            print(f"SKIP {label}: missing {key_name}")
            continue
        ok, detail = fn(key, args.timeout_s, args.user_agent)
        checked += 1
        if ok:
            print(f"OK   {label}: {detail}")
        else:
            print(f"FAIL {label}: {detail}")
            failures.append(f"{label}: {detail}")

    if checked == 0:
        print("FAIL: no API keys set to check")
        return 2
    if failures:
        print(f"Summary: FAIL checked={checked} failed={len(failures)}")
        return 1
    print(f"Summary: PASS checked={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
