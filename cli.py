"""
Command-line interface for yt_harvest.

Usage:
    yt-harvest search "python tutorial" ./output --min-duration 300 --max-duration 1800
    yt-harvest channel https://www.youtube.com/@SomeChannel ./output --min-duration 120
"""

import argparse
import sys

from .filters import FilterConfig
from .pipeline import channel_download, search_download


def _add_common_args(p):
    p.add_argument("output_dir", help="Directory to save downloaded audio files")
    p.add_argument("--min-duration", type=int, default=None, metavar="SECS",
                   help="Minimum video duration in seconds")
    p.add_argument("--max-duration", type=int, default=None, metavar="SECS",
                   help="Maximum video duration in seconds")
    p.add_argument("--format", choices=["wav", "mp3", "webm"], default=None,
                   dest="audio_format", help="Audio format (default: wav)")
    p.add_argument("--lang", default=None, dest="transcript_lang", metavar="CODE",
                   help="Subtitle language code, e.g. 'hi' or 'en'. Omit to skip subtitles.")
    p.add_argument("--rate-limit", default="10M", metavar="LIMIT",
                   help="Download speed cap, e.g. '10M' or '500K' (default: 10M)")
    p.add_argument("--archive", default="archive.txt", dest="download_archive",
                   metavar="FILE", help="Archive filename to avoid re-downloading")
    p.add_argument("--title-contains", nargs="+", default=None, metavar="WORD",
                   dest="title_must_contain",
                   help="Title must contain at least one of these words/phrases")
    p.add_argument("--title-not-contains", nargs="+", default=None, metavar="WORD",
                   dest="title_must_not_contain",
                   help="Title must not contain any of these words/phrases")
    p.add_argument("--no-filter", action="store_true",
                   help="Disable all content filters (music, singing, etc.)")
    p.add_argument("--allow-music", action="store_true",
                   help="Do not reject music / singing content")
    p.add_argument("--dry-run", action="store_true",
                   help="Discover and filter but do not download")


def _build_filter(args):
    if args.no_filter:
        return FilterConfig(
            reject_music=False,
            reject_singing=False,
            reject_compilations=False,
            reject_trailers=False,
            reject_reuploads=False,
        )
    return FilterConfig(
        reject_music=not args.allow_music,
        reject_singing=not args.allow_music,
        title_must_contain=args.title_must_contain,
        title_must_not_contain=args.title_must_not_contain,
    )


def cmd_search(args):
    filters = _build_filter(args)
    search_download(
        query=args.query,
        output_dir=args.output_dir,
        target_videos=args.target,
        search_batch_size=args.batch_size,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        filters=filters,
        audio_format=args.audio_format,
        transcript_lang=args.transcript_lang,
        rate_limit=args.rate_limit,
        download_archive=args.download_archive,
        dry_run=args.dry_run,
    )


def cmd_channel(args):
    filters = _build_filter(args)
    channel_download(
        channel_url=args.channel_url,
        output_dir=args.output_dir,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        video_type=args.video_type,
        max_results=args.max_results,
        filters=filters,
        audio_format=args.audio_format,
        transcript_lang=args.transcript_lang,
        rate_limit=args.rate_limit,
        download_archive=args.download_archive,
        dry_run=args.dry_run,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="yt-harvest",
        description="Download YouTube audio by search query or channel URL.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── search subcommand ─────────────────────────────────────────────────
    p_search = sub.add_parser("search", help="Search YouTube and download matching videos")
    p_search.add_argument("query", help="YouTube search query")
    _add_common_args(p_search)
    p_search.add_argument("--target", type=int, default=50, metavar="N",
                          help="Number of videos to download (default: 50)")
    p_search.add_argument("--batch-size", type=int, default=100, metavar="N",
                          dest="batch_size",
                          help="Videos to fetch per search round (default: 100)")
    p_search.set_defaults(func=cmd_search)

    # ── channel subcommand ────────────────────────────────────────────────
    p_channel = sub.add_parser("channel", help="Download from a YouTube channel")
    p_channel.add_argument("channel_url", help="Channel URL, e.g. https://www.youtube.com/@Name")
    _add_common_args(p_channel)
    p_channel.add_argument("--type", choices=["full", "shorts", "both"], default="full",
                           dest="video_type", help="Which videos to fetch (default: full)")
    p_channel.add_argument("--max-results", type=int, default=None, metavar="N",
                           help="Cap on videos inspected from the channel. Default: all.")
    p_channel.set_defaults(func=cmd_channel)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
