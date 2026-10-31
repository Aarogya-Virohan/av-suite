"""
Exercise media: tell the picture apart from the demo video.

`exercises.video_url` has always held whatever media link an exercise has.
Production data on 24 October 2026: 12 global exercises with Blogger image
links (no file extension), 8 clinic exercises with video file links, 1 empty.
Until the media model is redesigned with the founders' answer on personalised
photos (see docs/exercise-library/Decisions.md, EL-D-003), the API splits the
stored link into `image_url` and `demo_video_url` when it is read. Nothing in
the database changes.

Rules, kept deliberately strict:
- only absolute https links count; anything else (http, relative names such
  as "hamstring.mp4", data URIs) gives neither;
- a link is a video when its path ends in a video file extension or it points
  to a known video host; every other https link is treated as a picture.
"""

from __future__ import annotations

from urllib.parse import urlsplit

VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm", ".m3u8", ".ogv")
VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com")


def _https(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() != "https" or not parts.hostname:
        return None
    return url


def is_video_link(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in VIDEO_HOSTS):
        return True
    return parts.path.lower().endswith(VIDEO_EXTENSIONS)


def image_url(stored: str | None) -> str | None:
    """The picture link for an exercise, or None."""
    url = _https(stored)
    if url is None or is_video_link(url):
        return None
    return url


def demo_video_url(stored: str | None) -> str | None:
    """The demo video link for an exercise, or None."""
    url = _https(stored)
    if url is None or not is_video_link(url):
        return None
    return url
