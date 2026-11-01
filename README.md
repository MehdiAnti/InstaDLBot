# InstaDLBot

A Telegram bot for downloading Instagram Reels, posts, photos, videos, and carousel media. It uses **yt-dlp** for extraction, **python-telegram-bot** for Telegram integration, and **FastAPI** for webhook delivery.

## Features

- Instagram Reels, posts, and carousel media
- Photo, video, and document delivery, including large carousel batches
- Original Instagram description attached to the first delivered item, followed by the bot footer
- Private chat and group support
- Optional user allowlist and Instagram cookies
- Concurrent download control, per-file size limits, and download timeouts
- Temporary-file cleanup after delivery or failure
- Telegram webhook secret validation and startup retry handling
- Render deployment configuration

## Quick start

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Install Python 3.12 and FFmpeg.
3. Install dependencies: `pip install -r requirements.txt`.
4. Set `BOT_TOKEN` and `WEBHOOK_SECRET` in your environment.
5. Start locally with `PYTHONPATH=src uvicorn instadlbot.app:app --host 0.0.0.0 --port 8000`.

For local Telegram webhook testing, expose the server through an HTTPS tunnel and set `RENDER_EXTERNAL_URL` to its public base URL before startup.

## Deploy on Render

Connect the repository as a Render Web Service and use the included `render.yaml` Blueprint configuration. Set `BOT_TOKEN`; Render generates `WEBHOOK_SECRET` and provides `RENDER_EXTERNAL_URL`. The application registers its webhook during startup.

The service uses one Gunicorn/Uvicorn worker because the update queue and Telegram application are process-local. Do not increase the worker count without first changing the queue architecture.

## Configuration

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `BOT_TOKEN` | Yes | — | Telegram bot token |
| `WEBHOOK_SECRET` | Yes | Render-generated | Validates Telegram webhook requests |
| `RENDER_EXTERNAL_URL` | On Render | — | Public service URL used to register the webhook |
| `ALLOWED_USER_IDS` | No | Empty | Comma-separated Telegram user IDs; empty means no allowlist |
| `MAX_CONCURRENT_DOWNLOADS` | No | `2` | Maximum simultaneous download jobs |
| `MAX_FILE_SIZE_MB` | No | `49` | Maximum size of each downloaded file |
| `DOWNLOAD_TIMEOUT` | No | `180` | Download timeout in seconds |
| `INSTAGRAM_COOKIES_BASE64` | No | Empty | Optional Base64-encoded Netscape cookies file |
| `DOWNLOAD_DIR` | No | `/tmp/instadlbot` | Temporary working directory |

See [Configuration](docs/configuration.md) for details and examples.

## Group chats

To let the bot receive ordinary links in groups, disable its privacy mode with `/setprivacy` in @BotFather, then remove and re-add the bot to the group. Telegram otherwise limits which group messages the bot receives.

## Tests

~~~bash
pip install -r requirements-dev.txt
pytest -q
~~~

## Documentation

- [Architecture and request lifecycle](docs/architecture.md)
- [Configuration and environment variables](docs/configuration.md)
- [Libraries, tools, and implementation methods](docs/dependencies.md)
- [Local development and testing](docs/development.md)
- [Deployment and operations](docs/deployment.md)

## Limitations and responsible use

The bot can only download content Instagram makes available to the configured yt-dlp session. Private, restricted, deleted, or temporarily blocked content may not be accessible. Cookies do not bypass account permissions. Telegram's upload limits, Render Free resource limits, and Instagram's own restrictions apply.

Only download and share content you are authorized to access. Respect creators' rights and Instagram's terms.
