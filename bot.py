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
BOT_FOOTER = "@InstaDLPBot"
MAX_CAPTION_LENGTH = 1024


def extract_instagram_url(text):
    for candidate in URL_EXTRACTOR.findall(text or ""):
        candidate = candidate.rstrip(".,!?)]}")
        if URL_PATTERN.fullmatch(candidate):
            return candidate
    return None


def truncate_utf16(text, max_units):
    encoded = text.encode("utf-16-le")[:max_units * 2]
    return encoded.decode("utf-16-le", errors="ignore")


def build_media_caption(info):
    description = str(info.get("description") or "").strip()
    separator = "\n\n" if description else ""
    footer = f"{separator}{BOT_FOOTER}"
    available_units = MAX_CAPTION_LENGTH - len(footer.encode("utf-16-le")) // 2
    description = truncate_utf16(description, available_units).rstrip()
    return f"{description}{footer}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Send me a public Instagram post, Reel, or carousel link. "
        "I will download the available photos and videos and send them here. "
        "You can also add me to a group."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Supported links: Instagram posts, Reels, and carousels.\n"
        "You can use the bot in private chats and groups.\n"
        "Private posts and content requiring an account may not be accessible.\n"
        f"Maximum file size: {MAX_FILE_SIZE_MB} MB."
    )


async def send_single(bot, chat_id, kind, path, caption=None):
    with path.open("rb") as media:
        if kind == "photo":
            await bot.send_photo(chat_id=chat_id, photo=media, caption=caption)
        elif kind == "video":
            await bot.send_video(
                chat_id=chat_id,
                video=media,
                caption=caption,
                supports_streaming=True,
            )
        else:
            await bot.send_document(
                chat_id=chat_id,
                document=media,
                filename=path.name,
                caption=caption,
            )


async def send_group(bot, chat_id, items, caption=None):
    if len(items) == 1:
        kind, path = items[0]
        await send_single(bot, chat_id, kind, path, caption)
        return

    media = []
    handles = []

    try:
        for index, (kind, path) in enumerate(items):
            handle = path.open("rb")
            handles.append(handle)
            item_caption = caption if index == 0 else None

            if kind == "photo":
                media.append(InputMediaPhoto(media=handle, caption=item_caption))
            else:
                media.append(
                    InputMediaVideo(
                        media=handle,
                        caption=item_caption,
                        supports_streaming=True,
                    )
                )

        await bot.send_media_group(chat_id=chat_id, media=media)
    finally:
        for handle in handles:
            handle.close()


async def send_media(bot, chat_id, files, caption):
    batch = []
    caption_pending = caption

    for path in files:
        suffix = path.suffix.lower()

        if suffix in {".jpg", ".jpeg", ".png", ".webp"} and path.stat().st_size <= 10 * 1024 * 1024:
            kind = "photo"
        elif suffix in {".mp4", ".m4v", ".mov"}:
            kind = "video"
        else:
            kind = "document"

        if kind == "document":
            if batch:
                await send_group(bot, chat_id, batch, caption_pending)
                caption_pending = None
                batch = []

            await send_single(bot, chat_id, kind, path, caption_pending)
            caption_pending = None
            continue

        batch.append((kind, path))

        if len(batch) == 10:
            await send_group(bot, chat_id, batch, caption_pending)
            caption_pending = None
            batch = []

    if batch:
        await send_group(bot, chat_id, batch, caption_pending)


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
        return

    status = await context.bot.send_message(
        chat_id=message.chat_id,
        text="⏳ Queued. Preparing your download...",
    )

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
            caption = build_media_caption(info)
            await send_media(context.bot, message.chat_id, files, caption)

            await status.edit_text(f"✅ Done — {len(files)} file(s) sent.")
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
