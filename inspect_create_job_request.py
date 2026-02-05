import os, json
import httpx

base_url = os.getenv("BASE_URL", "https://dev-plt-studio-api.omniverba.net").rstrip("/")
spec = httpx.get(f"{base_url}/openapi.json", timeout=30).json()

schema = spec["components"]["schemas"]["CreateJobRequest"]
print(json.dumps(schema, indent=2, ensure_ascii=False))
