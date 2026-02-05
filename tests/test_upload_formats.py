import pytest
import httpx

# Небольшие "магические" заголовки/байты, чтобы файл был хоть как-то похож на формат.
# Нам не нужен валидный медиафайл — цель: проверить upload pipeline и поведение API по content_type/filename.
SAMPLES = [
    ("video_mp4", "sample.mp4", "video/mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64),
    ("audio_mp3", "sample.mp3", "audio/mpeg", b"ID3" + b"\x00" * 64),
    ("audio_wav", "sample.wav", "audio/wav", b"RIFF" + b"\x00" * 64 + b"WAVE"),
    ("random_pdf", "sample.pdf", "application/pdf", b"%PDF-1.7\n%EOF\n"),
    ("random_zip", "sample.zip", "application/zip", b"PK\x03\x04" + b"\x00" * 64),
    ("random_bin", "sample.bin", "application/octet-stream", b"\xDE\xAD\xBE\xEF" * 16),
    ("random_txt", "sample.txt", "text/plain", b"hello from api-tests\n"),
    ("random_exe", "sample.exe", "application/vnd.microsoft.portable-executable", b"MZ" + b"\x00" * 64),
]

@pytest.mark.e2e
@pytest.mark.parametrize("case_id,filename,content_type,content", SAMPLES)
def test_presigned_upload_accepts_or_rejects_formats_with_artifacts(client, artifacts, case_id, filename, content_type, content):
    """
    Попытки загрузить файлы разных типов через /uploads/presigned + presigned URL.
    В HTML-отчёт прикладываем все детали, чтобы было видно "что именно пробовали загрузить".
    """
    # 1) presigned request
    req_payload = {"filename": filename, "content_type": content_type}
    artifacts.add_kv(f"{case_id}_presigned_request", req_payload)

    pres = client.post("/uploads/presigned", json=req_payload)
    artifacts.add_kv(f"{case_id}_presigned_response_meta", {"status_code": pres.status_code, "headers": dict(pres.headers)})

    if pres.status_code in (401, 403):
        artifacts.add_text(f"{case_id}_skip_reason", "uploads/presigned requires auth; set API_TOKEN in .env")
        pytest.skip("uploads/presigned requires auth; set API_TOKEN in .env")

    # Некоторые API могут валидировать типы и отдавать 4xx/422 — это тоже полезный сигнал.
    if pres.status_code in (400, 422):
        if "application/json" in pres.headers.get("content-type",""):
            artifacts.add_json(f"{case_id}_presigned_error_body", pres.json())
        else:
            artifacts.add_text(f"{case_id}_presigned_error_body", pres.text[:800])
        # Не фейлим: фиксируем, что формат отвергнут корректно.
        return

    assert pres.status_code in (200, 201), f"Unexpected status from /uploads/presigned: {pres.status_code}"
    pres_json = pres.json()
    artifacts.add_json(f"{case_id}_presigned_response_body", pres_json)

    # 2) extract presigned fields
    upload_url = pres_json["upload_url"]
    method = str(pres_json["method"]).upper()
    bucket = pres_json.get("bucket")
    key = pres_json.get("key")
    expires_in = pres_json.get("expires_in")

    artifacts.add_kv(f"{case_id}_presigned_parsed", {
        "upload_url": upload_url,
        "method": method,
        "bucket": bucket,
        "key": key,
        "expires_in": expires_in,
    })

    # 3) record file details
    artifacts.add_kv(f"{case_id}_file", {
        "filename": filename,
        "content_type": content_type,
        "bytes_len": len(content),
        "first_bytes_hex": content[:16].hex(),
    })

    # 4) upload via absolute upload_url
    with httpx.Client(timeout=60, follow_redirects=True) as up:
        headers = {"Content-Type": content_type}

        if method == "PUT":
            up_res = up.put(upload_url, content=content, headers=headers)
        elif method == "POST":
            up_res = up.post(upload_url, content=content, headers=headers)
        else:
            artifacts.add_text(f"{case_id}_upload_error", f"Unsupported upload method: {method}")
            raise AssertionError(f"Unsupported upload method: {method}")

    # 5) store upload result in HTML
    body_preview = ""
    try:
        body_preview = up_res.text[:800]
    except Exception:
        body_preview = "<non-text body>"

    artifacts.add_kv(f"{case_id}_upload_result", {
        "status_code": up_res.status_code,
        "headers": dict(up_res.headers),
        "body_preview": body_preview,
    })

    # Успешная загрузка обычно 200/201/204. Если сервис отвечает 4xx — фиксируем и валим тест,
    # потому что presigned URL выдан, а загрузка не прошла.
    assert up_res.status_code in (200, 201, 204), f"Upload failed for {case_id}: {up_res.status_code}"
