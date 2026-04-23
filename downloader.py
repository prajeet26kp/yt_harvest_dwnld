import time
from datetime import datetime
from pathlib import Path

import yt_dlp

from .config import AUDIO_FORMAT, FORMAT_MAP, TRANSCRIPT_LANG


METADATA_KEYS = [
    "id", "webpage_url", "title", "uploader", "uploader_id", "uploader_url",
    "channel", "channel_id", "channel_url", "upload_date", "timestamp",
    "duration", "view_count", "like_count", "comment_count", "description",
    "language", "original_url", "tags", "categories", "age_limit",
    "availability", "live_status", "was_live", "acodec", "asr", "abr",
]


def extract_metadata(info):
    meta = {k: info.get(k) for k in METADATA_KEYS}
    meta["downloaded_at"] = datetime.now().isoformat()
    meta["audio_format"] = AUDIO_FORMAT
    return meta


def download_videos(
    video_ids,
    output_dir,
    audio_format=None,
    transcript_lang=None,
    rate_limit="10M",
    sleep_interval=0.1,
    max_sleep_interval=1,
    retries=10,
    download_archive="archive.txt",
    match_filter_fn=None,
):
    """
    Download audio (+ optional subtitles) for a list of video IDs.

    Args:
        video_ids:        Iterable of YouTube video ID strings.
        output_dir:       Root directory for downloads.
                          Files land at <output_dir>/<channel>/<title>.<ext>
        audio_format:     "wav" | "mp3" | "webm". Defaults to config.AUDIO_FORMAT.
        transcript_lang:  BCP-47 language code for subtitles (e.g. "hi", "en").
                          None disables subtitle download.
        rate_limit:       Download speed cap, e.g. "10M", "500K".
        download_archive: Filename (inside output_dir) tracking already-downloaded IDs.
        match_filter_fn:  Optional callable(info_dict) -> str | None.
                          Return a non-empty string to skip a video; None to proceed.

    Returns:
        dict with keys "downloaded", "skipped", "failed" — each a list of video IDs.
    """
    audio_format = audio_format or AUDIO_FORMAT
    transcript_lang = transcript_lang or TRANSCRIPT_LANG
    fmt = FORMAT_MAP.get(audio_format, FORMAT_MAP["webm"])

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_path = str(output_dir / download_archive)
    outtmpl = str(output_dir / "%(channel)s" / "%(title)s.%(ext)s")

    subtitle_opts = {}
    if transcript_lang:
        subtitle_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "vtt",
            "subtitleslangs": [transcript_lang],
        }

    postprocessors = []
    if audio_format in ("mp3", "wav"):
        pp = {"key": "FFmpegExtractAudio", "preferredcodec": audio_format}
        if audio_format == "mp3":
            pp["preferredquality"] = "0"
        postprocessors.append(pp)

    def _match_filter(info, *, incomplete):
        if incomplete:
            return None
        return match_filter_fn(info) if match_filter_fn else None

    ydl_opts = {
        "format": fmt["ydl_format"],
        "outtmpl": outtmpl,
        "ratelimit": _parse_rate_limit(rate_limit),
        "sleep_interval": sleep_interval,
        "max_sleep_interval": max_sleep_interval,
        "retries": retries,
        "fragment_retries": 15,
        "concurrent_fragment_downloads": 1,
        "download_archive": archive_path,
        "ignoreerrors": True,
        "quiet": False,
        "no_warnings": True,
        "continuedl": True,
        "noplaylist": True,
        "progress_hooks": [_build_progress_hook()],
        "postprocessor_hooks": [_build_postprocessor_hook()],
        "postprocessors": postprocessors,
        "match_filter": _match_filter,
        **subtitle_opts,
    }

    results = {"downloaded": [], "skipped": [], "failed": []}
    video_ids = list(video_ids)
    n = len(video_ids)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, vid in enumerate(video_ids, 1):
            url = f"https://www.youtube.com/watch?v={vid}"
            print(f"\n[{i}/{n}] {url}")
            try:
                ydl.download([url])
                results["downloaded"].append(vid)
            except Exception as e:
                if _is_fatal(str(e)):
                    print(f"FATAL: {e} — stopping downloads")
                    results["failed"].append(vid)
                    break
                print(f"Failed {vid}: {e}")
                results["failed"].append(vid)

    return results


# ── helpers ───────────────────────────────────────────────────────────────

def _build_progress_hook():
    def hook(d):
        if d.get("status") == "finished":
            info = d.get("info_dict", {})
            filename = d.get("filename", "")
            duration = info.get("duration")
            sleep_time = _dynamic_sleep(duration)
            print(f"  ✓ downloaded: {Path(filename).name}  ({duration}s) — sleeping {sleep_time}s")
            time.sleep(sleep_time)
    return hook


def _build_postprocessor_hook():
    def hook(d):
        status = d.get("status")
        postprocessor = d.get("postprocessor", "")
        filepath = d.get("info_dict", {}).get("filepath") or d.get("filepath", "")
        name = Path(filepath).name if filepath else "?"
        if status == "finished":
            if "FFmpegExtractAudio" in postprocessor:
                print(f"  ✓ wav:      {name}")
            elif "Subtitle" in postprocessor or "subtitle" in postprocessor.lower():
                print(f"  ✓ subtitle: {name}")
    return hook


def _dynamic_sleep(duration):
    """Scale post-download sleep with video length to avoid rate limits."""
    if not duration or duration <= 0:
        return 1.0
    # 0.1s for very short videos, up to 60s for 20-hour videos
    sleep_time = 0.1 + 59.9 * (duration / 72000)
    return round(max(2.0, sleep_time), 2)


def _is_fatal(msg):
    if not msg:
        return False
    msg = msg.lower()
    signals = [
        "http error 429", "too many requests", "rate limit",
        "unusual traffic", "automated requests", "captcha",
        "sign in to confirm",
    ]
    return any(s in msg for s in signals)


def _parse_rate_limit(rate_limit):
    rate_limit = rate_limit.strip().upper()
    if rate_limit.endswith("K"):
        return int(float(rate_limit[:-1]) * 1024)
    if rate_limit.endswith("M"):
        return int(float(rate_limit[:-1]) * 1024 * 1024)
    return int(rate_limit)
