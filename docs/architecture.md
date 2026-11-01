# Architecture

## Overview

The application is split into four runtime modules under `src/instadlbot/`:

| Module | Responsibility |
|---|---|
| `app.py` | FastAPI application, webhook endpoint, lifecycle, update queue, and worker |
| `bot.py` | Telegram handlers, URL extraction, captions, and media delivery |
| `downloader.py` | yt-dlp execution, file validation, timeout handling, and cleanup |
| `config.py` | Environment-variable parsing and optional cookie-file creation |

The package retains the existing responsibilities and processing flow. The `src/` layout is organizational rather than a redesign of bot behavior.

## Update lifecycle

1. FastAPI initializes the Telegram application.
2. If `RENDER_EXTERNAL_URL` is configured, the app registers `/telegram` with `WEBHOOK_SECRET`.
3. Telegram sends an update to `POST /telegram` with the secret-token header.
4. FastAPI validates the header, parses the update, and places it on the bounded in-memory queue.
5. A background worker passes queued updates to python-telegram-bot for handler dispatch.
6. The message handler checks the optional user allowlist and extracts a supported Instagram URL.
7. A semaphore limits concurrent downloads. yt-dlp runs in a worker thread.
8. Downloaded files are checked against supported extensions and the configured per-file size limit.
9. The bot sends individual photo/video/document messages or media groups, then removes the job's temporary directory.

## Runtime endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Basic service identity and status |
| `/health` | GET | Health status, queue size, and webhook configuration flag |
| `/telegram` | POST | Authenticated Telegram webhook receiver |

The webhook returns `403` for an invalid secret, `400` for an invalid update, and `503` when the in-memory queue is full.

## Concurrency model

A single background worker processes updates in queue order. Download concurrency is separately controlled by `DOWNLOAD_SEMAPHORE`. Gunicorn is configured with one Uvicorn worker because the queue and Telegram application are in-memory objects. Multiple web workers would create separate queues and bot instances.

## Media delivery

- Photo and video files are grouped into Telegram media groups of up to ten items.
- Documents are sent individually.
- The original Instagram description is attached to the first delivered item where possible, followed by `@InstaDLPBot`.
- Captions are truncated by UTF-16 code units to respect Telegram's 1,024-unit caption limit while preserving the footer.
- The bot edits its queued/downloading/sending status message. It does not send a final success status after delivery.

## Failure handling

Download failures become user-facing `DownloadError` messages. Unexpected processing or Telegram delivery errors are logged and produce a generic message. Temporary job directories are cleaned in the `finally` path; late results from timed-out thread tasks are also scheduled for cleanup.
