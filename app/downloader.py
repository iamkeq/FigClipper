from pathlib import Path

import yt_dlp

from app.config import DOWNLOADS_DIR


def download_youtube(url: str, job_id: str) -> Path:
    outtmpl = str(DOWNLOADS_DIR / f"{job_id}.%(ext)s")
    opts = {
        "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "noprogress": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    matches = list(DOWNLOADS_DIR.glob(f"{job_id}.*"))
    if not matches:
        raise RuntimeError("yt-dlp did not produce an output file")
    return matches[0]
