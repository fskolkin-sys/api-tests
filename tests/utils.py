import json
import logging
from typing import Any
import httpx

def is_cloudflare_challenge(resp: httpx.Response) -> bool:
    # Cloudflare/WAF blocks GitHub runners often -> returns 403 with HTML "Just a moment..."
    if resp.status_code != 403:
        return False
    h = {k.lower(): v for k, v in resp.headers.items()}
    if "cf-mitigated" in h:
        return True
    ct = h.get("content-type", "")
    if "text/html" in ct and "Just a moment" in (resp.text[:500] if resp.text else ""):
        return True
    return False


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
        if is_cloudflare_challenge(resp):
            import pytest
            pytest.skip("Blocked by Cloudflare/WAF in CI (cf-mitigated challenge)")
        log_response(resp, label=label or "unexpected_status")
    assert resp.status_code in expected, f"Expected {expected}, got {resp.status_code}"
