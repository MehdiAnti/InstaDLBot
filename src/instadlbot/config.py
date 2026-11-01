import base64
import binascii
import os
import re
from pathlib import Path


BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"].strip()
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
ALLOWED_USER_IDS = {
    int(value.strip())
    for value in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if value.strip().isdigit()
}
MAX_CONCURRENT_DOWNLOADS = max(1, int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2")))
MAX_FILE_SIZE_MB = max(1, int(os.getenv("MAX_FILE_SIZE_MB", "47")))
DOWNLOAD_TIMEOUT = max(30, int(os.getenv("DOWNLOAD_TIMEOUT", "180")))
INSTAGRAM_COOKIES_BASE64 = os.getenv("INSTAGRAM_COOKIES_BASE64", "").strip()
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/tmp/instadlbot"))
URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?(?:instagram\.com|instagr\.am)/(?:reel|reels|p|tv)/[A-Za-z0-9_.-]+/?(?:\?.*)?$",
    re.IGNORECASE,
)


def write_cookies_file():
    if not INSTAGRAM_COOKIES_BASE64:
        return None

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    cookie_path = DOWNLOAD_DIR / "cookies.txt"

    try:
        cookie_path.write_bytes(base64.b64decode(INSTAGRAM_COOKIES_BASE64, validate=True))
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError("INSTAGRAM_COOKIES_BASE64 is not valid Base64.") from exc

    return cookie_path
