import yt_dlp


def _extract_flat(url, max_results=None, quiet=True):
    """Extract flat playlist/search entries from a URL."""
    opts = {
        "quiet": quiet,
        "no_warnings": True,
        "extract_flat": True,
        "ignoreerrors": True,
    }
    if max_results:
        opts["playlistend"] = max_results

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        return []
    return info.get("entries", []) or []


def search_videos(query, max_results=100, quiet=True):
    """
    Search YouTube and return a list of flat entry dicts.
    Each entry contains: id, title, channel, channel_id, channel_url, duration, etc.
    """
    url = f"ytsearch{max_results}:{query}"
    return _extract_flat(url, max_results=max_results, quiet=quiet)


def get_channel_videos(channel_url, video_type="full", max_results=None, quiet=True):
    """
    Get videos from a channel.

    Args:
        channel_url: Full channel URL or channel ID.
        video_type:  "full" (default) | "shorts" | "both"
        max_results: Cap on number of videos fetched. None = all.
    """
    url = _resolve_channel_url(channel_url, video_type)
    return _extract_flat(url, max_results=max_results, quiet=quiet)


def normalize_channel_url(channel):
    """Ensure the channel identifier is a full URL."""
    channel = channel.strip()
    if channel.startswith("http://") or channel.startswith("https://"):
        return channel
    return f"https://www.youtube.com/channel/{channel}"


def _resolve_channel_url(channel_url, video_type):
    url = normalize_channel_url(channel_url).rstrip("/")
    if video_type == "shorts":
        return f"{url}/shorts"
    elif video_type == "full":
        return f"{url}/videos"
    return url  # "both" — the channel root
