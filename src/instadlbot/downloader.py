import asyncio
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yt_dlp

from .config import (
    DOWNLOAD_DIR,
    DOWNLOAD_TIMEOUT,
    MAX_FILE_SIZE_MB,
    write_cookies_file,
)


logger = logging.getLogger(__name__)
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
GALLERY_DL_TIMEOUT = max(1, min(90, DOWNLOAD_TIMEOUT - 15))
SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
    ".gif",
    ".mp4",
    ".m4v",
    ".mov",
}


class DownloadError(Exception):
    pass


def _find_valid_files(work_dir):
    files = sorted(
        path for path in work_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    valid_files = []
    oversized_files = []

    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            continue

        if not size:
            continue

        if size <= MAX_FILE_SIZE:
            valid_files.append(path)
        else:
            oversized_files.append(path)

    return valid_files, oversized_files


def _download_images_with_gallery_dl(url, work_dir, cookie_path):
    command = [
        sys.executable,
        "-m",
        "gallery_dl",
        "--config-ignore",
        "--no-input",
        "--no-mtime",
        "--no-part",
        "--quiet",
        "--filesize-max",
        str(MAX_FILE_SIZE),
        "--directory",
        str(work_dir),
    ]

    if cookie_path:
        command.extend(["--cookies", str(cookie_path)])

    command.append(url)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=GALLERY_DL_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        diagnostic = exc.stderr or exc.stdout or ""
        if isinstance(diagnostic, bytes):
            diagnostic = diagnostic.decode(errors="replace")
        logger.warning(
            "gallery-dl image fallback timed out after %s seconds: %s",
            GALLERY_DL_TIMEOUT,
            str(diagnostic).strip()[-1000:] or "No diagnostic output",
        )
        return

    if result.returncode:
        diagnostic = (result.stderr or result.stdout or "").strip()
        logger.warning(
            "gallery-dl image fallback exited with status %s: %s",
            result.returncode,
            diagnostic[-1500:] or "No diagnostic output",
        )


def _download_sync(url):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="job_", dir=DOWNLOAD_DIR))

    try:
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

        info = {}
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True) or {}
        except Exception as exc:
            logger.info(
                "yt-dlp did not extract media; trying image fallback (%s)",
                type(exc).__name__,
            )

        valid_files, oversized_files = _find_valid_files(work_dir)

        if not valid_files:
            _download_images_with_gallery_dl(url, work_dir, cookie_path)
            valid_files, oversized_files = _find_valid_files(work_dir)

        if not valid_files:
            if oversized_files:
                raise DownloadError(
                    f"Media exceeds the {MAX_FILE_SIZE_MB} MiB per-file download limit."
                )

            raise DownloadError(
                "Instagram did not provide downloadable media. The post may be "
                "unavailable, restricted, or temporarily blocked by Instagram."
            )

        return work_dir, valid_files, info

    except DownloadError:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        logger.warning("Instagram download failed: %s", type(exc).__name__)
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
