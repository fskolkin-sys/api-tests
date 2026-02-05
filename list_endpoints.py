import os
import json
import httpx

base_url = os.getenv("BASE_URL", "https://dev-plt-studio-api.omniverba.net").rstrip("/")
token = os.getenv("API_TOKEN", "").strip()

headers = {"Accept": "application/json"}
if token:
    headers["Authorization"] = f"Bearer {token}"

r = httpx.get(f"{base_url}/openapi.json", headers=headers, timeout=30)
r.raise_for_status()
spec = r.json()

paths = spec.get("paths", {})
items = []
for path, methods in paths.items():
    for m in methods.keys():
        items.append((m.upper(), path))

items.sort(key=lambda x: (x[1], x[0]))

print(f"Base URL: {base_url}")
print(f"Total endpoints: {len(items)}")
for m, p in items:
    print(f"{m:6} {p}")
