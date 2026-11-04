import json
import time
from pathlib import Path

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

from app.config import GEMINI_API_KEY, GEMINI_MODEL

_MAX_RETRIES = 4
_RETRY_BACKOFF_S = 10
_REQUEST_TIMEOUT_MS = 180_000  # 3 minutes per request, so a hung model surfaces as an error

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


def _is_rate_limited(exc: ClientError) -> bool:
    return exc.code == 429


def _generate_with_retry(client: genai.Client, prompt: str, uploaded):
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[uploaded, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except ServerError:
            if attempt == _MAX_RETRIES:
                raise
            time.sleep(_RETRY_BACKOFF_S * attempt)
        except ClientError as exc:
            if attempt == _MAX_RETRIES or not _is_rate_limited(exc):
                raise
            time.sleep(_RETRY_BACKOFF_S * attempt)


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, ClientError) and _is_rate_limited(exc):
        return (
            "Gemini API rate limit reached. Wait a bit and try again, or check your "
            "plan's quota."
        )
    if isinstance(exc, ClientError) and exc.code in (401, 403):
        return "Gemini API key is invalid or unauthorized. Check GEMINI_API_KEY."
    if isinstance(exc, ClientError) and exc.code == 404:
        return (
            f'Gemini model "{GEMINI_MODEL}" is not available for this API key. '
            "Try a different GEMINI_MODEL."
        )
    if isinstance(exc, ServerError):
        return "Gemini is currently overloaded or unavailable. Try again in a few minutes."
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return "Gemini did not respond in time. Try again."
    if isinstance(exc, APIError):
        return f"Gemini API error: {exc.message}"
    return f"Gemini request failed: {exc}"


def analyze_video(
    video_path: Path, max_clips: int, min_length_s: float, max_length_s: float
) -> list[dict]:
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key is not configured. Set GEMINI_API_KEY.")

    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
    )

    try:
        uploaded = client.files.upload(file=str(video_path))
        uploaded = _wait_until_active(client, uploaded.name)

        prompt = PROMPT_TEMPLATE.format(
            max_clips=max_clips, min_length=min_length_s, max_length=max_length_s
        )
        try:
            response = _generate_with_retry(client, prompt, uploaded)
        finally:
            client.files.delete(name=uploaded.name)
    except (APIError, httpx.TimeoutException, TimeoutError) as exc:
        raise RuntimeError(_friendly_error(exc)) from exc

    text = response.text.strip()
    try:
        clips = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini returned a response that wasn't valid JSON.") from exc
    if not isinstance(clips, list):
        raise RuntimeError("Gemini did not return a JSON array of clips.")
    return clips[:max_clips]
