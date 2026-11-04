import json
import time
from pathlib import Path

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL

PROMPT_TEMPLATE = """You are selecting the best short-form clips from this video for \
posting as standalone social media shorts (like TikTok/YouTube Shorts/Reels).

Watch the whole video and pick up to {max_clips} self-contained moments that would work \
as engaging short clips, each between {min_length}s and {max_length}s long. Favor moments \
with a clear hook, a complete thought or punchline, humor, strong emotion, or a surprising \
statement. Do not pick overlapping ranges.

Respond with ONLY a JSON array (no markdown, no commentary) where each item has this shape:
{{"start_s": <number, seconds>, "end_s": <number, seconds>, "title": <short catchy title>, \
"slug": <2-6 words describing what happens in the clip, lowercase, hyphen-separated, \
filename-safe, e.g. "dog-steals-sandwich">, "reason": <one sentence on why this clip works>}}
"""


def _wait_until_active(client: genai.Client, file_name: str, timeout_s: int = 600):
    waited = 0
    while waited < timeout_s:
        f = client.files.get(name=file_name)
        if f.state.name == "ACTIVE":
            return f
        if f.state.name == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {f.name}")
        time.sleep(3)
        waited += 3
    raise TimeoutError("Timed out waiting for Gemini to process the video")


def analyze_video(
    video_path: Path, max_clips: int, min_length_s: float, max_length_s: float
) -> list[dict]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=GEMINI_API_KEY)

    uploaded = client.files.upload(file=str(video_path))
    uploaded = _wait_until_active(client, uploaded.name)

    prompt = PROMPT_TEMPLATE.format(
        max_clips=max_clips, min_length=min_length_s, max_length=max_length_s
    )
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[uploaded, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
    finally:
        client.files.delete(name=uploaded.name)

    text = response.text.strip()
    clips = json.loads(text)
    if not isinstance(clips, list):
        raise ValueError("Gemini did not return a JSON array of clips")
    return clips[:max_clips]
