from typing import Optional

from pydantic import BaseModel


class Clip(BaseModel):
    index: int
    title: str
    reason: str
    start_s: float
    end_s: float
    filename: str


class Job(BaseModel):
    id: str
    status: str  # queued | downloading | uploading | analyzing | clipping | done | error
    source_type: str  # "upload" | "url"
    source: str  # original filename or URL
    vertical: bool
    created_at: float
    error: Optional[str] = None
    clips: list[Clip] = []
