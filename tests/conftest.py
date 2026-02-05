import os
import json
import pytest
import httpx

# -----------------------
# базовые фикстуры клиента
# -----------------------

def _validate_base_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise RuntimeError(
            f"BASE_URL must start with http:// or https://, got: {url!r}. "
            "Fix GitHub Actions secrets/env or your local .env."
        )
    return url

@pytest.fixture(scope="session")
def base_url() -> str:
    raw = os.getenv("BASE_URL", "https://dev-plt-studio-api.omniverba.net")
    return _validate_base_url(raw)

@pytest.fixture(scope="session")
def api_token() -> str:
    return os.getenv("API_TOKEN", "").strip()

@pytest.fixture(scope="session")
def headers(api_token: str) -> dict:
    h = {"Accept": "application/json"}
    if api_token:
        h["Authorization"] = f"Bearer {api_token}"
    return h

@pytest.fixture
def client(base_url: str, headers: dict):
    with httpx.Client(
        base_url=base_url,
        timeout=30,
        follow_redirects=True,
        headers=headers,
    ) as c:
        yield c

# -----------------------
# артефакты в HTML-отчёт
# -----------------------

def _safe_json(obj):
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False, default=str))
    except Exception:
        return {"repr": repr(obj)}

def _response_body(resp: httpx.Response, limit: int = 2000):
    ct = resp.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            return resp.json()
        except Exception:
            return resp.text[:limit]
    try:
        return resp.text[:limit]
    except Exception:
        return "<non-text body>"

@pytest.fixture
def artifacts(request):
    """
    artifacts.add_json("name", {...})
    artifacts.add_text("name", "...")
    artifacts.add_kv("name", {"a": 1})
    artifacts.add_http("name", resp) -> meta + body
    """
    store = []

    class Artifacts:
        def add_json(self, name: str, data):
            store.append(("json", name, _safe_json(data)))

        def add_text(self, name: str, text: str):
            store.append(("text", name, str(text)))

        def add_kv(self, name: str, data: dict):
            store.append(("json", name, _safe_json(data)))

        def add_http(self, name: str, resp: httpx.Response, body_limit: int = 2000):
            # meta
            meta = {
                "method": resp.request.method if resp.request else None,
                "url": str(resp.request.url) if resp.request else None,
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
            }
            self.add_kv(f"{name}_meta", meta)

            # body
            body = _response_body(resp, limit=body_limit)
            if isinstance(body, (dict, list)):
                self.add_json(f"{name}_body", body)
            else:
                self.add_text(f"{name}_body_preview", body)

    request.node._artifacts = store
    return Artifacts()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call":
        return

    pytest_html = item.config.pluginmanager.getplugin("html")
    if not pytest_html:
        return

    extras = getattr(rep, "extras", [])
    store = getattr(item, "_artifacts", [])
    for kind, name, payload in store:
        if kind == "json":
            content = json.dumps(payload, ensure_ascii=False, indent=2)
            extras.append(pytest_html.extras.text(content, name=f"{name}.json"))
        else:
            extras.append(pytest_html.extras.text(payload, name=f"{name}.txt"))

    rep.extras = extras
