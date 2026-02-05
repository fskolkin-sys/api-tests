import json
import logging
from typing import Any
import httpx

log = logging.getLogger("api-tests")

def pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        return repr(obj)

def log_response(resp: httpx.Response, label: str = "") -> None:
    """Call this when debugging or on assertion failure."""
    prefix = f"[{label}] " if label else ""
    ct = resp.headers.get("content-type", "")
    body = None
    if "application/json" in ct:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
    else:
        body = resp.text[:800]

    log.info("%sHTTP %s %s", prefix, resp.request.method, resp.request.url)
    log.info("%sStatus: %s", prefix, resp.status_code)
    log.info("%sHeaders: %s", prefix, dict(resp.headers))
    log.info("%sBody: %s", prefix, pretty(body))

def assert_status(resp: httpx.Response, expected: set[int], label: str = "") -> None:
    if resp.status_code not in expected:
        log_response(resp, label=label or "unexpected_status")
    assert resp.status_code in expected, f"Expected {expected}, got {resp.status_code}"
