import asyncio
import logging
import re

from telegram import InputMediaPhoto, InputMediaVideo, Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

from config import (
    ALLOWED_USER_IDS,
    MAX_CONCURRENT_DOWNLOADS,
    MAX_FILE_SIZE_MB,
    URL_PATTERN,
)
from downloader import DownloadError, cleanup_download, download_media


logger = logging.getLogger(__name__)
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
URL_EXTRACTOR = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


def extract_instagram_url(text):
    for candidate in URL_EXTRACTOR.findall(text or ""):
        candidate = candidate.rstrip(".,!?)]}")
        if URL_PATTERN.fullmatch(candidate):
            return candidate
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a public Instagram post, Reel, or carousel link. "
        "I will download the available photos and videos and send them here."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Supported links: Instagram posts, Reels, and carousels.\n"
        "Private posts and content requiring an account may not be accessible.\n"
        f"Maximum file size: {MAX_FILE_SIZE_MB} MB."
    )


async def send_media(message, files):
    if len(files) == 1:
        path = files[0]
        with path.open("rb") as media:
            is_photo = path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            if is_photo and path.stat().st_size <= 10 * 1024 * 1024:
                await message.reply_photo(photo=media)
            elif is_photo:
                await message.reply_document(document=media, filename=path.name)
            else:
                await message.reply_video(video=media, supports_streaming=True)
        return

    group = []
    for path in files:
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} and path.stat().st_size <= 10 * 1024 * 1024:
            group.append(("photo", path))
        elif path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
            group.append(("video", path))
        else:
            group.append(("document", path))

    batch = []
    for kind, path in group:
        if kind == "document":
            if batch:
                await send_group(message, batch)
                batch = []
            with path.open("rb") as media:
                await message.reply_document(document=media, filename=path.name)
            continue

        batch.append((kind, path))
        if len(batch) == 10:
            await send_group(message, batch)
            batch = []

    if batch:
        await send_group(message, batch)


async def send_group(message, items):
    media = []
    handles = []

    try:
        for kind, path in items:
            handle = path.open("rb")
            handles.append(handle)
            if kind == "photo":
                media.append(InputMediaPhoto(media=handle))
            else:
                media.append(InputMediaVideo(media=handle, supports_streaming=True))

        await message.reply_media_group(media=media)
    finally:
        for handle in handles:
            handle.close()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    if ALLOWED_USER_IDS and user.id not in ALLOWED_USER_IDS:
        await message.reply_text("Sorry, this bot is private.")
        return

    url = extract_instagram_url(message.text or message.caption or "")
    if not url:
        await message.reply_text("Please send a valid Instagram post, Reel, or carousel URL.")
        return

    status = await message.reply_text("⏳ Queued. Preparing your download...")

    async with DOWNLOAD_SEMAPHORE:
        work_dir = None
        try:
            await status.edit_text("⬇️ Downloading Instagram media...")
            await context.bot.send_chat_action(
                chat_id=message.chat_id,
                action=ChatAction.UPLOAD_DOCUMENT,
            )

            work_dir, files, info = await download_media(url)

            await status.edit_text(f"📤 Sending {len(files)} file(s) to Telegram...")
            await send_media(message, files)

            title = info.get("title") or info.get("description") or "Instagram media"
            title = " ".join(str(title).split())
            if len(title) > 100:
                title = title[:97] + "..."

            await status.edit_text(f"✅ Done — {len(files)} file(s) sent.\n{title}")
        except DownloadError as exc:
            await status.edit_text(f"❌ {exc}")
        except Exception:
            logger.exception("Failed to process an Instagram link")
            await status.edit_text(
                "❌ Telegram could not send this media. It may exceed Telegram's "
                "upload limits. Try another post or a smaller file."
            )
        finally:
            cleanup_download(work_dir)


def build_application(token):
    request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=30,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=30,
        media_write_timeout=120,
    )
    application = (
        Application.builder()
        .token(token)
        .request(request)
        .concurrent_updates(True)
        .build()
    )
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/start(?:@\w+)?$"), start))
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/help(?:@\w+)?$"), help_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, handle_message))
    return application
