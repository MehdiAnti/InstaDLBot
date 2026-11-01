import asyncio
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import instadlbot.app as app_module
from instadlbot.bot import build_media_caption, extract_instagram_url


def test_accepts_reel():
    assert extract_instagram_url("https://www.instagram.com/reel/ABC123/") == (
        "https://www.instagram.com/reel/ABC123/"
    )


def test_accepts_post_with_query():
    url = "https://www.instagram.com/p/ABC123/?img_index=2"
    assert extract_instagram_url(url) == url


def test_rejects_non_instagram_url():
    assert extract_instagram_url("https://example.com/reel/ABC123/") is None


def test_extracts_url_from_message():
    assert extract_instagram_url("Download this: https://instagram.com/reels/ABC123/") == (
        "https://instagram.com/reels/ABC123/"
    )


def test_rejects_instagram_profile():
    assert extract_instagram_url("https://www.instagram.com/someuser/") is None


def test_caption_includes_instagram_description_and_bot_footer():
    caption = build_media_caption({"description": "Original Instagram caption"})
    assert caption == "Original Instagram caption\n\n@InstaDLPBot"


def test_caption_always_keeps_bot_footer_with_long_description():
    caption = build_media_caption({"description": "x" * 2000})
    assert caption.endswith("@InstaDLPBot")
    assert len(caption.encode("utf-16-le")) // 2 <= 1024


def test_caption_uses_footer_when_description_is_missing():
    assert build_media_caption({}) == "@InstaDLPBot"


def test_root_supports_head_requests():
    response = TestClient(app_module.app).head("/")
    assert response.status_code == 200


def test_health_supports_head_requests():
    response = TestClient(app_module.app).head("/health")
    assert response.status_code == 200


def test_webhook_rejects_invalid_secret():
    response = TestClient(app_module.app).post(
        "/telegram",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "incorrect"},
    )
    assert response.status_code == 403


def test_webhook_rejects_non_object_payload():
    response = TestClient(app_module.app).post(
        "/telegram",
        json=[],
        headers={
            "X-Telegram-Bot-Api-Secret-Token": app_module.WEBHOOK_SECRET,
        },
    )
    assert response.status_code == 400


def test_shutdown_does_not_delete_registered_webhook(monkeypatch):
    class FakeTelegramApplication:
        def __init__(self):
            self.bot = type("FakeBot", (), {})()
            self.bot.set_webhook = AsyncMock()
            self.bot.delete_webhook = AsyncMock()
            self.initialize = AsyncMock()
            self.start = AsyncMock()
            self.stop = AsyncMock()
            self.shutdown = AsyncMock()
            self.process_update = AsyncMock()

    fake_application = FakeTelegramApplication()
    monkeypatch.setattr(app_module, "telegram_app", fake_application)
    monkeypatch.setattr(app_module, "RENDER_EXTERNAL_URL", "https://example.com")
    monkeypatch.setattr(app_module, "WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setattr(app_module, "worker_task", None)

    async def run_lifespan():
        async with app_module.lifespan(app_module.app):
            await asyncio.sleep(0)

    asyncio.run(run_lifespan())

    fake_application.bot.set_webhook.assert_awaited_once()
    fake_application.bot.delete_webhook.assert_not_awaited()
    fake_application.stop.assert_awaited_once()
    fake_application.shutdown.assert_awaited_once()
