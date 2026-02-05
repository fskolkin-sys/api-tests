import pytest
import httpx

SAMPLES = [
    ("video_mp4", "sample.mp4", "video/mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64),
    ("audio_mp3", "sample.mp3", "audio/mpeg", b"ID3" + b"\x00" * 64),
    ("audio_wav", "sample.wav", "audio/wav", b"RIFF" + b"\x00" * 64 + b"WAVE"),
    ("random_pdf", "sample.pdf", "application/pdf", b"%PDF-1.7\n%EOF\n"),
    ("random_zip", "sample.zip", "application/zip", b"PK\x03\x04" + b"\x00" * 64),
    ("random_bin", "sample.bin", "application/octet-stream", b"\xDE\xAD\xBE\xEF" * 16),
    ("random_txt", "sample.txt", "text/plain", b"hello from api-tests\n"),
]

@pytest.mark.e2e
@pytest.mark.parametrize("case_id,filename,content_type,content", SAMPLES)
def test_presigned_upload_attempts_are_logged_in_html_report(client, artifacts, base_url, case_id, filename, content_type, content):
    """
    Для каждого формата:
    - логируем presigned request + response (meta+body)
    - логируем upload request + response (meta+body_preview)
    - логируем summary (что пытались, чем закончилось)
    """
    artifacts.add_kv(f"{case_id}_context", {
        "base_url": base_url,
        "case_id": case_id,
        "filename": filename,
        "content_type": content_type,
        "bytes_len": len(content),
        "first_bytes_hex": content[:16].hex(),
    })

    # 1) presigned
    presigned_payload = {"filename": filename, "content_type": content_type}
    artifacts.add_kv(f"{case_id}_presigned_request", presigned_payload)

    pres = client.post("/uploads/presigned", json=presigned_payload)
    artifacts.add_http(f"{case_id}_presigned_response", pres)

    if pres.status_code in (401, 403):
        artifacts.add_kv(f"{case_id}_summary", {"result": "SKIP_AUTH", "presigned_status": pres.status_code})
        pytest.skip("uploads/presigned requires auth; set API_TOKEN in .env / GitHub secrets")

    # 400/422 = формат/пейлоад отклонён политикой — это валидный исход, фиксируем и выходим без FAIL
    if pres.status_code in (400, 422):
        artifacts.add_kv(f"{case_id}_summary", {"result": "REJECTED", "presigned_status": pres.status_code})
        return

    assert pres.status_code in (200, 201), f"{case_id}: unexpected presigned status {pres.status_code}"

    pres_json = pres.json()
    upload_url = pres_json["upload_url"]
    method = str(pres_json["method"]).upper()
    bucket = pres_json.get("bucket")
    key = pres_json.get("key")

    # 2) upload request meta
    artifacts.add_kv(f"{case_id}_upload_request", {
        "upload_url": upload_url,
        "method": method,
        "content_type": content_type,
        "bytes_len": len(content),
        "bucket": bucket,
        "key": key,
    })

    # 3) upload to presigned url
    with httpx.Client(timeout=60, follow_redirects=True) as up:
        headers = {"Content-Type": content_type}
        if method == "PUT":
            up_res = up.put(upload_url, content=content, headers=headers)
        elif method == "POST":
            up_res = up.post(upload_url, content=content, headers=headers)
        else:
            artifacts.add_kv(f"{case_id}_summary", {"result": "FAIL_UNSUPPORTED_METHOD", "method": method})
            raise AssertionError(f"{case_id}: unsupported upload method {method}")

    artifacts.add_http(f"{case_id}_upload_response", up_res)

    ok = up_res.status_code in (200, 201, 204)
    artifacts.add_kv(f"{case_id}_summary", {
        "result": "UPLOADED_OK" if ok else "UPLOAD_FAILED",
        "presigned_status": pres.status_code,
        "upload_status": up_res.status_code,
        "gcs_hint": f"gs://{bucket}/{key}" if bucket and key else None,
    })

    assert ok, f"{case_id}: upload failed with {up_res.status_code}"
