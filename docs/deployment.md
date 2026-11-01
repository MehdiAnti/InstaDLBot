# Deployment and operations

## Render Blueprint

`render.yaml` defines the Render Web Service, Python runtime, build command, Gunicorn start command, and environment settings. The start command changes into `src` before importing `instadlbot.app`, matching the standard `src/` layout.

1. Connect the GitHub repository to Render.
2. Create the Web Service from the Blueprint.
3. Set `BOT_TOKEN` to the token issued by @BotFather.
4. Keep the generated `WEBHOOK_SECRET` private.
5. Deploy and check logs for Telegram initialization and webhook registration.

Render provides `RENDER_EXTERNAL_URL`. When present, the app registers `https://<service-host>/telegram` as the Telegram webhook.

## Process model

Gunicorn runs with `uvicorn_worker.UvicornWorker` and exactly one worker. The update queue and Telegram application are process-local; multiple web workers would each have separate state.

The HTTP handler validates and queues updates. A background task processes them. The queue is bounded to 1,000 updates; when full, the webhook returns HTTP 503 so Telegram can retry delivery.

## Health checks

- `GET /` returns basic service status.
- `GET /health` reports status, queue size, and whether a public webhook URL is configured.

These endpoints do not prove Instagram can currently serve a particular post.

## Render Free considerations

- Free services may sleep after inactivity; the first request after sleep can be delayed.
- CPU, memory, and ephemeral disk are limited.
- Downloads use `/tmp` and are not persistent application data.
- Job directories are removed after processing; restarts discard ephemeral files.
- Large media, long downloads, Instagram throttling, and Telegram upload limits can cause individual jobs to fail.

## Troubleshooting

| Symptom | Things to check |
|---|---|
| Bot does not respond | Render logs, `BOT_TOKEN`, service health, and webhook registration |
| Webhook returns 403 | Confirm Telegram sends the configured `WEBHOOK_SECRET` |
| Bot misses group links | Disable BotFather privacy mode, then remove and re-add the bot |
| Instagram download fails | Post may be private, unavailable, restricted, rate-limited, or require cookies |
| File is not sent | Check configured file size and Telegram upload constraints |
| Startup cannot reach Telegram | Check outbound connectivity; startup calls retry transient network errors |
| Queue reports busy | Queue reached 1,000 updates; inspect worker processing and service resources |

## Secret handling

Never paste bot tokens or cookies into issue reports or logs. Store them as Render environment variables. If a token or cookie is exposed, revoke or rotate it immediately and update the service environment.
