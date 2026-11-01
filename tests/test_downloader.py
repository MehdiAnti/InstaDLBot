from pathlib import Path
from subprocess import CompletedProcess

import instadlbot.downloader as downloader


def test_photo_only_post_uses_gallery_dl_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "DOWNLOAD_DIR", tmp_path)
    monkeypatch.setattr(downloader, "write_cookies_file", lambda: None)

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def extract_info(self, url, download):
            return {"description": "Photo post caption", "entries": [None, None]}

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYoutubeDL)

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_dir = Path(command[command.index("--directory") + 1])
        (output_dir / "photo_1.jpg").write_bytes(b"image-one")
        (output_dir / "photo_2.jpg").write_bytes(b"image-two")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(downloader.subprocess, "run", fake_run)

    work_dir, files, info = downloader._download_sync(
        "https://www.instagram.com/p/ABC123/"
    )

    try:
        assert [path.name for path in files] == ["photo_1.jpg", "photo_2.jpg"]
        assert info["description"] == "Photo post caption"
        assert "--config-ignore" in captured["command"]
        assert "--filesize-max" in captured["command"]
        assert captured["kwargs"]["check"] is False
    finally:
        downloader.cleanup_download(work_dir)


def test_gallery_dl_fallback_receives_cookie_file(tmp_path, monkeypatch):
    cookie_path = tmp_path / "cookies.txt"
    cookie_path.write_text("# Netscape HTTP Cookie File")

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(downloader.subprocess, "run", fake_run)

    downloader._download_images_with_gallery_dl(
        "https://www.instagram.com/p/ABC123/",
        tmp_path,
        cookie_path,
    )

    assert captured["command"][captured["command"].index("--cookies") + 1] == str(
        cookie_path
    )


def test_gallery_dl_fallback_uses_bounded_file_size(tmp_path, monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(downloader.subprocess, "run", fake_run)

    downloader._download_images_with_gallery_dl(
        "https://www.instagram.com/p/ABC123/",
        tmp_path,
        None,
    )

    size_index = captured["command"].index("--filesize-max")
    assert captured["command"][size_index + 1] == str(downloader.MAX_FILE_SIZE)



def test_find_valid_files_discovers_nested_gallery_dl_output(tmp_path):
    nested_dir = tmp_path / "instagram" / "user" / "post"
    nested_dir.mkdir(parents=True)
    photo = nested_dir / "photo.jpg"
    photo.write_bytes(b"image")

    valid_files, oversized_files = downloader._find_valid_files(tmp_path)

    assert valid_files == [photo]
    assert oversized_files == []


def test_gallery_dl_timeout_still_recovers_downloaded_files(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "DOWNLOAD_DIR", tmp_path)
    monkeypatch.setattr(downloader, "write_cookies_file", lambda: None)

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def extract_info(self, url, download):
            return {"description": "Photo post caption", "entries": [None]}

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYoutubeDL)

    def fake_run(command, **kwargs):
        output_dir = Path(command[command.index("--directory") + 1])
        nested_dir = output_dir / "instagram" / "user" / "post"
        nested_dir.mkdir(parents=True)
        (nested_dir / "photo.jpg").write_bytes(b"image")
        raise downloader.subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(downloader.subprocess, "run", fake_run)

    work_dir, files, info = downloader._download_sync(
        "https://www.instagram.com/p/ABC123/"
    )

    try:
        assert [path.name for path in files] == ["photo.jpg"]
        assert info["description"] == "Photo post caption"
    finally:
        downloader.cleanup_download(work_dir)
