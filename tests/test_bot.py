import asyncio

import pytest
from telegram import ReplyParameters

from instadlbot.bot import send_group, send_single


class FakeBot:
    def __init__(self):
        self.calls = []

    async def send_photo(self, **kwargs):
        self.calls.append(("photo", kwargs))

    async def send_video(self, **kwargs):
        self.calls.append(("video", kwargs))

    async def send_document(self, **kwargs):
        self.calls.append(("document", kwargs))

    async def send_media_group(self, **kwargs):
        self.calls.append(("media_group", kwargs))


@pytest.mark.parametrize(
    ("kind", "filename", "method"),
    [
        ("photo", "photo.jpg", "photo"),
        ("video", "video.mp4", "video"),
        ("document", "file.bin", "document"),
    ],
)
def test_single_media_replies_to_source_message(tmp_path, kind, filename, method):
    path = tmp_path / filename
    path.write_bytes(b"media")
    bot = FakeBot()

    asyncio.run(
        send_single(
            bot,
            123,
            kind,
            path,
            caption="caption",
            reply_to_message_id=456,
        )
    )

    call_name, kwargs = bot.calls[0]
    assert call_name == method
    assert kwargs["reply_parameters"] == ReplyParameters(message_id=456)


def test_media_group_replies_to_source_message(tmp_path):
    paths = [tmp_path / "one.jpg", tmp_path / "two.mp4"]
    for path in paths:
        path.write_bytes(b"media")

    bot = FakeBot()

    asyncio.run(
        send_group(
            bot,
            123,
            [("photo", paths[0]), ("video", paths[1])],
            caption="caption",
            reply_to_message_id=456,
        )
    )

    call_name, kwargs = bot.calls[0]
    assert call_name == "media_group"
    assert kwargs["reply_parameters"] == ReplyParameters(message_id=456)
