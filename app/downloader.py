from pathlib import Path

import yt_dlp

from app.config import DOWNLOADS_DIR


def download_youtube(url: str, job_id: str) -> Path:
    outtmpl = str(DOWNLOADS_DIR / f"{job_id}.%(ext)s")
    opts = {
        # YouTube currently requires a PO token for most formats on the "web" client,
        # so we prefer "android"/"tv" clients, which still expose at least a muxed
        # progressive format without one. Falls back to whatever is available.
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "noprogress": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    matches = list(DOWNLOADS_DIR.glob(f"{job_id}.*"))
    if not matches:
        raise RuntimeError("yt-dlp did not produce an output file")
    return matches[0]
