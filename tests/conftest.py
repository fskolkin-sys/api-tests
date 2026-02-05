import os
import json
import pytest
import httpx

# -----------------------
# базовые фикстуры клиента
# -----------------------

@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("BASE_URL", "https://dev-plt-studio-api.omniverba.net").rstrip("/")

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

@pytest.fixture
def artifacts(request):
    """
    artifacts.add_json("name", {...})
    artifacts.add_text("name", "...")
    artifacts.add_kv("name", {"a":1})
    Всё это прикрепится к HTML-отчёту для текущего теста.
    """
    store = []

    class Artifacts:
        def add_json(self, name: str, data):
            store.append(("json", name, _safe_json(data)))

        def add_text(self, name: str, text: str):
            store.append(("text", name, str(text)))

        def add_kv(self, name: str, data: dict):
            store.append(("json", name, _safe_json(data)))

        def dump(self):
            return list(store)

    request.node._artifacts = store  # для hook ниже
    return Artifacts()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Прикрепляет artifacts к pytest-html report.
    Делает это всегда (на call-фазе), чтобы и PASSED тесты имели полезные данные.
    """
    outcome = yield
    rep = outcome.get_result()

    if rep.when != "call":
        return

    # pytest-html может быть не установлен — тогда просто ничего
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
