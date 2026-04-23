from .discovery import search_videos, get_channel_videos
from .filters import FilterConfig, filter_videos
from .downloader import download_videos


def search_download(
    query,
    output_dir,
    *,
    # How many videos to actually download (keeps searching until target is hit)
    target_videos=50,
    search_batch_size=100,
    # Convenience duration shortcuts (set on FilterConfig if you need more)
    min_duration=None,
    max_duration=None,
    # Full filter control
    filters: FilterConfig = None,
    # Download options
    audio_format=None,
    transcript_lang=None,
    rate_limit="10M",
    download_archive="archive.txt",
    # Dry-run: discover + filter but don't download
    dry_run=False,
):
    """
    Search YouTube for *query* and download matching videos.

    Keeps issuing search batches until *target_videos* have been downloaded
    (or YouTube runs out of results).

    Args:
        query:            YouTube search string.
        output_dir:       Where to save audio files.
        target_videos:    Stop after downloading this many videos.
        search_batch_size: Videos to fetch per search round.
        min_duration:     Minimum video length in seconds (shortcut for FilterConfig).
        max_duration:     Maximum video length in seconds (shortcut for FilterConfig).
        filters:          FilterConfig instance for full control. When None a default
                          FilterConfig() is used (rejects music, singing, etc.).
        audio_format:     "wav" | "mp3" | "webm".
        transcript_lang:  BCP-47 code for subtitle download (e.g. "hi"). None = skip.
        rate_limit:       Download speed cap, e.g. "10M".
        download_archive: Filename tracking already-downloaded IDs.
        dry_run:          If True, discover and filter but do not download.

    Returns:
        dict: searched, passed_filter, downloaded, failed
    """
    cfg = _make_config(filters, min_duration, max_duration)

    total_searched = 0
    total_downloaded = 0
    total_failed = 0
    search_offset = 0

    print(f"[search_download] query={query!r}  target={target_videos}")

    while total_downloaded < target_videos:
        remaining = target_videos - total_downloaded
        # Overfetch to account for filtering losses
        fetch_n = min(search_batch_size, remaining * 4)

        print(f"  Searching: offset={search_offset} batch={fetch_n} ...")
        entries = _search_with_offset(query, max_results=fetch_n, offset=search_offset)

        if not entries:
            print("  No more results — stopping.")
            break

        total_searched += len(entries)
        search_offset += len(entries)

        passed, rejected = filter_videos(entries, cfg, return_rejected=True)
        _print_rejection_summary(rejected)

        if not passed:
            print(f"  0/{len(entries)} passed — continuing search")
            continue

        # Cap to what we still need
        to_download = passed[: target_videos - total_downloaded]

        if dry_run:
            total_downloaded += len(to_download)
            continue

        video_ids = [e["id"] for e in to_download if e and e.get("id")]
        print(f"  Downloading {len(video_ids)} videos ...")
        result = download_videos(
            video_ids=video_ids,
            output_dir=output_dir,
            audio_format=audio_format,
            transcript_lang=transcript_lang,
            rate_limit=rate_limit,
            download_archive=download_archive,
        )
        total_downloaded += len(result["downloaded"])
        total_failed += len(result["failed"])
        print(f"  Progress: {total_downloaded}/{target_videos}")

    print(
        f"\n[search_download] done — "
        f"searched={total_searched}  downloaded={total_downloaded}  failed={total_failed}"
    )
    return {
        "searched": total_searched,
        "downloaded": total_downloaded,
        "failed": total_failed,
    }


def channel_download(
    channel_url,
    output_dir,
    *,
    # Convenience duration shortcuts
    min_duration=None,
    max_duration=None,
    # Channel options
    video_type="full",
    max_results=None,
    # Full filter control
    filters: FilterConfig = None,
    # Download options
    audio_format=None,
    transcript_lang=None,
    rate_limit="10M",
    download_archive="archive.txt",
    # Cap downloads this session (None = no limit)
    max_downloads=None,
    # Dry-run: discover + filter but don't download
    dry_run=False,
):
    """
    Download videos from a YouTube channel that match the given criteria.

    Walks the full channel video list (or up to *max_results*), filters by
    duration and any other criteria, then downloads matching videos.

    Args:
        channel_url:   Full channel URL, e.g. https://www.youtube.com/@SomeChannel
        output_dir:    Where to save audio files.
        min_duration:  Minimum video length in seconds.
        max_duration:  Maximum video length in seconds.
        video_type:    "full" (default) | "shorts" | "both"
        max_results:   Cap on how many channel videos to inspect. None = all.
        filters:       FilterConfig for full control. Defaults to FilterConfig().
        audio_format:  "wav" | "mp3" | "webm".
        transcript_lang: BCP-47 code for subtitle download. None = skip.
        rate_limit:    Download speed cap, e.g. "10M".
        download_archive: Filename tracking already-downloaded IDs.
        max_downloads: Cap on videos actually downloaded this session. None = all that pass filters.
        dry_run:       If True, discover and filter but do not download.

    Returns:
        dict: found, passed_filter, downloaded, failed
    """
    cfg = _make_config(filters, min_duration, max_duration)

    print(f"[channel_download] {channel_url}  type={video_type}  max={max_results}")
    entries = get_channel_videos(channel_url, video_type=video_type, max_results=max_results)
    print(f"  Found {len(entries)} videos on channel")

    passed, rejected = filter_videos(entries, cfg, return_rejected=True)
    _print_rejection_summary(rejected)
    print(f"  Passed filters: {len(passed)} / {len(entries)}")

    if dry_run or not passed:
        return {
            "found": len(entries),
            "passed_filter": len(passed),
            "downloaded": 0,
            "failed": 0,
        }

    video_ids = [r["id"] for r in passed if r and r.get("id")]
    if max_downloads is not None:
        video_ids = video_ids[:max_downloads]
    print(f"  Downloading {len(video_ids)} videos ...")
    result = download_videos(
        video_ids=video_ids,
        output_dir=output_dir,
        audio_format=audio_format,
        transcript_lang=transcript_lang,
        rate_limit=rate_limit,
        download_archive=download_archive,
    )

    print(
        f"\n[channel_download] done — "
        f"found={len(entries)}  passed={len(passed)}  "
        f"downloaded={len(result['downloaded'])}  failed={len(result['failed'])}"
    )
    return {
        "found": len(entries),
        "passed_filter": len(passed),
        "downloaded": len(result["downloaded"]),
        "failed": len(result["failed"]),
    }


# ── helpers ───────────────────────────────────────────────────────────────

def _make_config(filters, min_duration, max_duration):
    """Merge convenience duration args with an explicit FilterConfig."""
    cfg = filters if filters is not None else FilterConfig()
    if min_duration is not None:
        cfg.min_duration = min_duration
    if max_duration is not None:
        cfg.max_duration = max_duration
    return cfg


def _search_with_offset(query, max_results, offset=0):
    """
    yt-dlp doesn't support search pagination natively, so we fetch
    offset+max_results and slice off the already-seen portion.
    """
    import yt_dlp

    total = offset + max_results
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "ignoreerrors": True,
        "playlistend": total,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{total}:{query}", download=False)
    if not info:
        return []
    entries = info.get("entries", []) or []
    return entries[offset:]


def _print_rejection_summary(rejected):
    if not rejected:
        return
    reasons = {}
    for _, reason in rejected:
        reasons[reason] = reasons.get(reason, 0) + 1
    if reasons:
        summary = "  Rejections: " + ", ".join(
            f"{r}={c}" for r, c in sorted(reasons.items(), key=lambda x: -x[1])
        )
        print(summary)
