# Dependencies and implementation methods

Exact Python package versions are maintained in `requirements.txt`. Development-only dependencies are in `requirements-dev.txt`.

## Runtime libraries

| Library | Purpose | Main APIs and methods |
|---|---|---|
| FastAPI | HTTP app and webhook | `FastAPI`, route decorators, `HTTPException`, `Header`, `Request`, `Response`, lifespan |
| Uvicorn | ASGI server | Uvicorn worker used by Gunicorn |
| Gunicorn | Process manager | `uvicorn_worker.UvicornWorker`, one worker |
| python-telegram-bot | Telegram integration | `Application`, `Update`, `MessageHandler`, `filters`, `HTTPXRequest`, media input classes, bot send and webhook methods |
| yt-dlp | Instagram Reels and video extraction and download | `yt_dlp.YoutubeDL`, `YoutubeDL.extract_info`, downloader options |
| gallery-dl | Instagram image posts and photo carousels; used when yt-dlp does not produce media files | Python module CLI, Instagram extractor, cookie-file support |
| pytest | Unit tests | Test discovery and assertion runner; development dependency |

## System dependency

**FFmpeg** is installed by Render through `apt.txt`. yt-dlp uses FFmpeg/FFprobe when media processing or merging requires them. Local development should also have FFmpeg on `PATH`.

## Python standard library

- `asyncio.Queue` buffers webhook updates.
- `asyncio.create_task`, `asyncio.to_thread`, `asyncio.wait_for`, `asyncio.Semaphore`, and `asyncio.sleep` handle lifecycle tasks, blocking-download isolation, timeouts, concurrency, and retries.
- `tempfile.mkdtemp`, `pathlib.Path`, and `shutil.rmtree` manage isolated temporary jobs and cleanup.
- `base64.b64decode` decodes optional cookie data.
- `re` extracts and validates Instagram URLs.
- `logging` records operational diagnostics.

## Implementation details

### Webhook processing

FastAPI validates `X-Telegram-Bot-Api-Secret-Token` before queue insertion. `Update.de_json` converts the incoming JSON payload into a Telegram update object.

### yt-dlp

A fresh `YoutubeDL` instance is created for each download job. The format selector prefers MP4 when available and falls back to the best available format. Playlist handling remains enabled for carousel content. Output files are filtered by supported extension and file size.

### Instagram photo fallback

yt-dlp remains the primary downloader for Reels and video media. Instagram photo-only posts are handled by gallery-dl because yt-dlp does not provide image-post downloading. The fallback uses the same optional Netscape cookies file, writes into the job's temporary directory, disables external gallery-dl configuration, and enforces the configured per-file size limit. The normal file validation and cleanup path applies to both downloaders.

### Thread offloading and timeout

`YoutubeDL.extract_info` is synchronous, so `_download_sync` runs through `asyncio.to_thread`. `asyncio.wait_for` enforces the configured timeout. A running thread cannot be forcibly stopped; if it finishes after timeout, a completion callback cleans its temporary directory.

### Telegram media methods

Photo/video batches use `send_media_group` with `InputMediaPhoto` / `InputMediaVideo`. Documents and single media items use `send_document`, `send_photo`, or `send_video`. File handles stay open until the Telegram request completes.

### Logging

The `httpx` and `httpcore` loggers are reduced to WARNING. This avoids verbose HTTP request logs, which can contain sensitive Bot API request URLs.
