import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import CLIPS_DIR, UPLOADS_DIR
from app.jobs import store
from app.runner import new_job, submit

app = FastAPI(title="FigClipper")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/jobs")
async def create_job(
    url: Optional[str] = Form(None),
    vertical: bool = Form(True),
    file: Optional[UploadFile] = None,
):
    if not url and not file:
        raise HTTPException(400, "Provide either a url or a file")
    if url and file:
        raise HTTPException(400, "Provide only one of url or file")

    if url:
        job = new_job("url", url, vertical)
        submit(job.id, None, url)
    else:
        job = new_job("upload", file.filename or "upload.mp4", vertical)
        suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
        dest = UPLOADS_DIR / f"{job.id}{suffix}"
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        submit(job.id, dest, None)

    return job


@app.get("/api/jobs")
def list_jobs():
    return store.list()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    job_clip_dir = CLIPS_DIR / job_id
    if job_clip_dir.exists():
        shutil.rmtree(job_clip_dir)
    store.delete(job_id)
    return {"ok": True}


@app.get("/api/jobs/{job_id}/clips/{filename}")
def get_clip(job_id: str, filename: str):
    safe_name = Path(filename).name
    path = CLIPS_DIR / job_id / safe_name
    if not path.is_file():
        raise HTTPException(404, "Clip not found")
    return FileResponse(path, media_type="video/mp4", filename=safe_name)


app.mount("/", StaticFiles(directory="static", html=True), name="static")
