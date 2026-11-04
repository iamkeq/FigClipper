FROM denoland/deno:bin-2.9.5 AS deno-bin

FROM node:22-trixie-slim AS bgutil-build

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch 2.0.2 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git

WORKDIR /opt/bgutil-ytdlp-pot-provider/server
RUN npm ci --no-audit --no-fund \
    && npx tsc \
    && npm prune --omit=dev


FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libjpeg62-turbo libgif7 librsvg2-2 \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp needs a PO token to fetch anything above ~360p from YouTube; this ships
# a Node runtime plus the compiled bgutil-ytdlp-pot-provider "script" mode provider
# that yt-dlp-get-pot picks up automatically at ~/bgutil-ytdlp-pot-provider/server.
COPY --from=bgutil-build /usr/local/bin/node /usr/local/bin/node
COPY --from=bgutil-build /opt/bgutil-ytdlp-pot-provider /root/bgutil-ytdlp-pot-provider

# yt-dlp also wants a JS runtime (Deno by default) to run YouTube's player JS for
# signature/format deciphering; without it, some higher-quality formats are missing.
COPY --from=deno-bin /deno /usr/local/bin/deno

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

ENV DATA_DIR=/app/data
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
