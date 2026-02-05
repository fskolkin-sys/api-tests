from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Optional, Any, Dict

class HealthResponse(BaseModel):
    # у разных сервисов бывает по-разному; оставляем гибко
    status: Optional[str] = None
    ok: Optional[bool] = None
    detail: Optional[str] = None

class ReadyResponse(BaseModel):
    status: Optional[str] = None
    ok: Optional[bool] = None

class PresignedUploadResponse(BaseModel):
    bucket: str
    key: str
    upload_url: AnyHttpUrl
    method: str
    expires_in: int = Field(ge=1)

class CreateJobResponse(BaseModel):
    job_id: Optional[str] = None
    id: Optional[str] = None

    def resolved_id(self) -> str:
        jid = self.job_id or self.id
        if not jid:
            raise ValueError("Missing job_id/id")
        return jid

class JobStatusResponse(BaseModel):
    # schema неизвестна — оставляем гибко, но проверяем ключевые вещи
    status: Optional[str] = None
    state: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Any] = None
