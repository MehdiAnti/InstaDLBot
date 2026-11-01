import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

import yt_dlp

from config import (
    DOWNLOAD_DIR,
    DOWNLOAD_TIMEOUT,
    MAX_FILE_SIZE_MB,
    write_cookies_file,
)


logger = logging.getLogger(__name__)
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".m4v", ".mov"}


class DownloadError(Exception):
    pass


def _download_sync(url):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="job_", dir=DOWNLOAD_DIR))
    cookie_path = write_cookies_file()

    options = {
        "outtmpl": str(work_dir / "%(autonumber)02d_%(id)s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": False,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "max_filesize": MAX_FILE_SIZE,
        "writethumbnail": False,
        "extractor_retries": 2,
    }

    if cookie_path:
        options["cookiefile"] = str(cookie_path)

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            raise DownloadError("Instagram did not return any media.")

        files = sorted(
            path for path in work_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        valid_files = []
        for path in files:
            try:
                size = path.stat().st_size
            except OSError:
                continue

            if size and size <= MAX_FILE_SIZE:
                valid_files.append(path)

        if not valid_files:
            raise DownloadError(
                f"No media within the {MAX_FILE_SIZE_MB} MB file limit was downloaded."
            )

        return work_dir, valid_files, info

    except DownloadError:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        logger.warning("Instagram download failed: %s", exc)
        raise DownloadError(
            "Could not download this post. It may be private, unavailable, "
            "age-restricted, or temporarily blocked by Instagram."
        ) from exc


def _cleanup_late_result(task):
    try:
        result = task.result()
        cleanup_download(result[0])
    except Exception:
        pass


async def download_media(url):
    task = asyncio.create_task(asyncio.to_thread(_download_sync, url))

    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=DOWNLOAD_TIMEOUT)
    except asyncio.TimeoutError as exc:
        task.add_done_callback(_cleanup_late_result)
        raise DownloadError("The download took too long. Please try again later.") from exc


def cleanup_download(path):
    if path:
        shutil.rmtree(path, ignore_errors=True)
