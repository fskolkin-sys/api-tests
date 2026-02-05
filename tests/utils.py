import httpx
import logging
import pytest

log = logging.getLogger("api-tests")

def log_response(resp: httpx.Response, label: str = "") -> None:
    log.info("[%s] HTTP %s %s", label, resp.request.method, resp.request.url)
    log.info("[%s] Status: %s", label, resp.status_code)
    log.info("[%s] Headers: %s", label, dict(resp.headers))
    try:
        log.info("[%s] Body: %r", label, resp.text[:1000])
    except Exception:
        log.info("[%s] Body: <non-text>", label)

def is_cloudflare_challenge(resp: httpx.Response) -> bool:
    if resp.status_code != 403:
        return False
    h = {k.lower(): v for k, v in resp.headers.items()}
    if "cf-mitigated" in h:
        return True
    ct = h.get("content-type", "")
    if "text/html" in ct:
        body = ""
        try:
            body = resp.text[:500]
        except Exception:
            pass
        if "Just a moment" in body or "cloudflare" in body.lower():
            return True
    return False

def assert_status(resp: httpx.Response, expected: set[int], label: str = "") -> None:
    if resp.status_code not in expected:
        if is_cloudflare_challenge(resp):
            # ---- ВАЖНО: артефакт в HTML ----
            item = pytest._current_request.node  # type: ignore
            artifacts = getattr(item, "_artifacts", None)
            if artifacts is not None:
                artifacts.append((
                    "json",
                    f"{label or 'request'}_cloudflare_detected",
                    {
                        "reason": "Blocked by Cloudflare / WAF",
                        "status_code": resp.status_code,
                        "headers": dict(resp.headers),
                        "body_preview": (resp.text[:500] if resp.text else ""),
                    },
                ))
            pytest.skip("Blocked by Cloudflare/WAF (cf-mitigated challenge in CI)")
        log_response(resp, label=label or "unexpected_status")
    assert resp.status_code in expected, f"Expected {expected}, got {resp.status_code}"
