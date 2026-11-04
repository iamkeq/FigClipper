# FigClipper

Point it at a video file or a YouTube URL, Gemini watches the whole thing and picks the
best short-form moments, ffmpeg cuts them into standalone clips (optionally cropped to
vertical 9:16) in a simple web UI.

## How it works

1. You submit a video (upload or URL) through the web UI.
2. If it's a URL, `yt-dlp` downloads it.
3. The video is uploaded to Gemini's Files API and analyzed with a prompt asking for the
   best clip-worthy moments as timestamp ranges.
4. `ffmpeg` cuts each range into its own `.mp4` (optionally center-cropped to 9:16).
5. Clips show up in the UI with previews and download links.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000.

You'll also need `ffmpeg` installed on your machine (`brew install ffmpeg`).

## Running in Docker (homelab)

```bash
cp .env.example .env   # fill in GEMINI_API_KEY
docker compose up -d --build
```

This builds an image with `ffmpeg` baked in, runs the API/UI on port `8420`, and
persists uploads/downloads/clips under `./data` (bind-mounted into the container).

To update after pulling new code:

```bash
docker compose up -d --build
```

## Configuration

Set these via `.env` (local) or environment variables (Docker):

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Required. Your Gemini API key. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model used for clip analysis. |
| `MAX_CLIPS` | `5` | Max number of clips to generate per video. |
| `DATA_DIR` | `data` | Where uploads/downloads/clips/job state are stored. |

## Notes

- Clip cutting re-encodes (rather than stream-copies) so cut points are frame-accurate.
- Jobs and their clip metadata persist to `data/jobs.json`; clip files live under
  `data/clips/<job_id>/`.
- There's no auth — if you expose this beyond your LAN, put it behind a reverse proxy
  with its own access control.
