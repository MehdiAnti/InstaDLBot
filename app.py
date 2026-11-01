import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, Response
from telegram import Update

from bot import build_application
from config import BOT_TOKEN, RENDER_EXTERNAL_URL, WEBHOOK_SECRET


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
telegram_app = build_application(BOT_TOKEN)
update_queue = asyncio.Queue(maxsize=1000)
worker_task = None


async def update_worker():
    while True:
        update = await update_queue.get()
        try:
            await telegram_app.process_update(update)
        except Exception:
            logger.exception("Failed to process Telegram update")
        finally:
            update_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task

    await telegram_app.initialize()
    await telegram_app.start()

    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/telegram"
        await telegram_app.bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )
        logger.info("Telegram webhook configured")

    worker_task = asyncio.create_task(update_worker())

    yield

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    if RENDER_EXTERNAL_URL:
        await telegram_app.bot.delete_webhook()

    await telegram_app.stop()
    await telegram_app.shutdown()


app = FastAPI(title="InstaDLBot", lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "ok", "service": "InstaDLBot"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "queue_size": update_queue.qsize(),
        "webhook_configured": bool(RENDER_EXTERNAL_URL),
    }


@app.post("/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        payload = await request.json()
        update = Update.de_json(payload, telegram_app.bot)
        update_queue.put_nowait(update)
    except asyncio.QueueFull:
        raise HTTPException(status_code=503, detail="Bot is busy")
    except (json.JSONDecodeError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid update")

    return Response(status_code=200)
