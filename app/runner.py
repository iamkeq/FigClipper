import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from app.clipper import cut_clip, get_duration
from app.config import CLIPS_DIR, MAX_CLIPS
from app.downloader import download_youtube
from app.gemini_client import analyze_video
from app.jobs import store
from app.models import Clip, Job

_executor = ThreadPoolExecutor(max_workers=2)


def new_job(source_type: str, source: str, vertical: bool) -> Job:
    job = Job(
        id=uuid.uuid4().hex[:12],
        status="queued",
        source_type=source_type,
        source=source,
        vertical=vertical,
        created_at=time.time(),
    )
    store.put(job)
    return job


def submit(job_id: str, video_path: Optional[Path], url: Optional[str]) -> None:
    _executor.submit(_run, job_id, video_path, url)


def _set_status(job: Job, status: str) -> None:
    job.status = status
    store.put(job)


def _run(job_id: str, video_path: Optional[Path], url: Optional[str]) -> None:
    job = store.get(job_id)
    if job is None:
        return

    try:
        if url is not None:
            _set_status(job, "downloading")
            video_path = download_youtube(url, job_id)

        assert video_path is not None
        duration = get_duration(video_path)

        _set_status(job, "analyzing")
        raw_clips = analyze_video(video_path, MAX_CLIPS)

        _set_status(job, "clipping")
        job_clip_dir = CLIPS_DIR / job_id
        job_clip_dir.mkdir(parents=True, exist_ok=True)

        clips: list[Clip] = []
        for i, c in enumerate(raw_clips):
            start_s = max(0.0, float(c["start_s"]))
            end_s = min(duration, float(c["end_s"]))
            if end_s <= start_s:
                continue
            filename = f"clip_{i + 1}.mp4"
            cut_clip(video_path, start_s, end_s, job_clip_dir / filename, job.vertical)
            clips.append(
                Clip(
                    index=i + 1,
                    title=str(c.get("title", f"Clip {i + 1}")),
                    reason=str(c.get("reason", "")),
                    start_s=start_s,
                    end_s=end_s,
                    filename=filename,
                )
            )

        job.clips = clips
        _set_status(job, "done")
    except Exception as exc:  # noqa: BLE001
        job.error = str(exc)
        _set_status(job, "error")
