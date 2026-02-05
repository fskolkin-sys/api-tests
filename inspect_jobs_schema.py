import os, json
import httpx

base_url = os.getenv("BASE_URL", "https://dev-plt-studio-api.omniverba.net").rstrip("/")
token = os.getenv("API_TOKEN", "").strip()

headers = {"Accept": "application/json"}
if token:
    headers["Authorization"] = f"Bearer {token}"

spec = httpx.get(f"{base_url}/openapi.json", headers=headers, timeout=30).json()

jobs = spec["paths"]["/jobs"]["post"]

print("=== POST /jobs summary ===")
print("operationId:", jobs.get("operationId"))
print("tags:", jobs.get("tags"))
print("security:", jobs.get("security"))

req = jobs.get("requestBody", {})
content = req.get("content", {})
app_json = content.get("application/json", {})

print("\n=== requestBody ===")
print("required:", req.get("required"))
print("content-types:", list(content.keys()))

schema = app_json.get("schema")
example = app_json.get("example")
examples = app_json.get("examples")

print("\n=== schema (raw) ===")
print(json.dumps(schema, indent=2, ensure_ascii=False))

if example is not None:
    print("\n=== example ===")
    print(json.dumps(example, indent=2, ensure_ascii=False))

if examples is not None:
    print("\n=== examples ===")
    print(json.dumps(examples, indent=2, ensure_ascii=False))

# Also print the validation error format if we send empty payload (helpful)
print("\n=== server validation error for {} payload ===")
r = httpx.post(f"{base_url}/jobs", headers={**headers, "Content-Type": "application/json"}, json={}, timeout=30)
print("status:", r.status_code)
ct = r.headers.get("content-type", "")
if "application/json" in ct:
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
else:
    print(r.text[:500])
