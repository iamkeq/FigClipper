import json
import subprocess
from pathlib import Path


def get_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def cut_clip(src: Path, start_s: float, end_s: float, dest: Path, vertical: bool) -> None:
    duration = max(0.5, end_s - start_s)
    cmd = ["ffmpeg", "-y", "-ss", str(max(0.0, start_s)), "-i", str(src), "-t", str(duration)]

    if vertical:
        vf = (
            "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        )
        cmd += ["-vf", vf]

    cmd += [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
