import json
import threading
from typing import Optional

from app.config import JOBS_FILE
from app.models import Job


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._load()

    def _load(self) -> None:
        if not JOBS_FILE.exists():
            return
        raw = json.loads(JOBS_FILE.read_text())
        self._jobs = {jid: Job(**data) for jid, data in raw.items()}

    def _save(self) -> None:
        JOBS_FILE.write_text(
            json.dumps({jid: job.model_dump() for jid, job in self._jobs.items()}, indent=2)
        )

    def put(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job
            self._save()

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def delete(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)
            self._save()


store = JobStore()
