from bot import extract_instagram_url


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
