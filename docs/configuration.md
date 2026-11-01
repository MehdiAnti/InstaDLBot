# Configuration

All settings are read from environment variables. Required settings are validated when the configuration module is imported.

| Variable | Required | Default | Description |
|---|---:|---|---|
| `BOT_TOKEN` | Yes | — | Token issued by @BotFather |
| `WEBHOOK_SECRET` | Yes | — | Secret token expected in Telegram's webhook header |
| `RENDER_EXTERNAL_URL` | No | Empty | Public base URL; when set, webhook is registered at `/telegram` |
| `ALLOWED_USER_IDS` | No | Empty | Comma-separated numeric Telegram user IDs allowed to use the bot |
| `MAX_CONCURRENT_DOWNLOADS` | No | `2` | Concurrent download limit; values are clamped to at least 1 |
| `MAX_FILE_SIZE_MB` | No | `47` | Maximum size of each downloaded file in MiB; values are clamped to at least 1 |
| `DOWNLOAD_TIMEOUT` | No | `180` | Download timeout in seconds; values are clamped to at least 30 |
| `INSTAGRAM_COOKIES_BASE64` | No | Empty | Base64-encoded Netscape-format cookies data |
| `DOWNLOAD_DIR` | No | `/tmp/instadlbot` | Parent directory for temporary jobs and optional cookies |

The default 47 MiB download cap leaves a margin below Telegram's standard 50 MB bot upload ceiling. Images larger than Telegram's 10 MB `sendPhoto` limit are sent as documents instead. Files above the configured per-file cap are skipped.

## Restricting access

Set `ALLOWED_USER_IDS` to Telegram numeric user IDs separated by commas:

~~~env
ALLOWED_USER_IDS=123456789,987654321
~~~

If the variable is empty, the bot does not apply a user allowlist.

## Instagram cookies

Export a Netscape-format cookies file from a browser session you own, encode its contents as Base64, and store the result in `INSTAGRAM_COOKIES_BASE64`. The application decodes it into `cookies.txt` under `DOWNLOAD_DIR` and passes it to yt-dlp.

Cookies are credentials: do not commit them, include them in logs, or share them. They do not grant permission to content your account cannot access.

## Security notes

- Keep `BOT_TOKEN`, `WEBHOOK_SECRET`, and cookie data in hosting-provider secret settings.
- Do not add `.env`, cookies, or downloaded media to version control.
- Rotate any exposed Telegram token or session cookies.
- The webhook secret is checked before update parsing and queue insertion.
