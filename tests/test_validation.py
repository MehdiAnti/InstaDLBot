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
