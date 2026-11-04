from pathlib import Path

import yt_dlp

from app.config import DOWNLOADS_DIR

_BASE_OPTS = {
    "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "merge_output_format": "mp4",
    "quiet": True,
    "noprogress": True,
}

# Fetching above ~360p requires a PO token on most clients. The bgutil PO token
# provider (bundled in the Docker image) supplies one, letting yt-dlp use its own
# best client chain at full quality. Without that provider (e.g. local dev outside
# Docker), that default chain fails outright, so we fall back to forcing the
# "android" client, which still exposes a muxed progressive format with no token.
_FALLBACK_EXTRACTOR_ARGS = {"youtube": {"player_client": ["android", "web"]}}


def download_youtube(url: str, job_id: str) -> Path:
    outtmpl = str(DOWNLOADS_DIR / f"{job_id}.%(ext)s")

    try:
        with yt_dlp.YoutubeDL({**_BASE_OPTS, "outtmpl": outtmpl}) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError:
        fallback_opts = {
            **_BASE_OPTS,
            "outtmpl": outtmpl,
            "extractor_args": _FALLBACK_EXTRACTOR_ARGS,
        }
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            ydl.download([url])

    matches = list(DOWNLOADS_DIR.glob(f"{job_id}.*"))
    if not matches:
        raise RuntimeError("yt-dlp did not produce an output file")
    return matches[0]
