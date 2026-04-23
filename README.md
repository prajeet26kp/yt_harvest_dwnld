# yt-harvest

Download YouTube audio by **search query** or **channel URL**, with duration, title, and content filtering.

---

## Quickstart

Install, edit `proc.py`, run:

```bash
pip install -e .
python proc.py
```

`proc.py` contains three ready-to-run examples — search download, channel download, and fine-grained filter control. **Edit the parameters at the top of the file and execute it directly.** That's the fastest way to get started.

```python
from yt_harvest import search_download, channel_download, FilterConfig


# ── Example 1: search-based download ──────────────────────────────────────────
# Downloads Hindi podcast/interview audio (5–30 min) until 50 files are saved.

search_download(
    query="hindi podcast interview",
    output_dir="./audio/search",
    target_videos=50,
    min_duration=300,       # 5 min
    max_duration=1800,      # 30 min
    audio_format="wav",
    transcript_lang="hi",   # also saves .hi.vtt subtitle files; set None to skip
    rate_limit="10M",
)


# ── Example 2: channel download ────────────────────────────────────────────────
# Downloads all full videos (10–60 min) from a specific channel.




channel_download(
    channel_url="https://www.youtube.com/@AmazonMXPlayer",
    output_dir="./audio/channel",
    min_duration=1200,  
    max_results=60, 
    max_downloads=30,
    audio_format="wav",
    transcript_lang="hi",
    rate_limit="10M",
    filters=FilterConfig(
          title_must_contain=["Episode", "episodes"],                                                                                                                
      ),                                                                                                                                                                                               
)



# ── Example 3: fine-grained FilterConfig ──────────────────────────────────────
# Full control: title keywords, view floor, date range, custom rejections.

filters = FilterConfig(
    min_duration=300,
    max_duration=1800,
    title_must_contain=["episode", "ep", "podcast"],    # ANY of these keeps it
    title_must_not_contain=["shorts", "clip", "promo"], # ANY of these rejects it
    min_views=1000,
    uploaded_after="20230101",   # YYYYMMDD
    reject_music=True,
    reject_singing=True,
    reject_compilations=True,
    reject_trailers=True,
    reject_reuploads=True,
)

search_download(
    query="comedy podcast hindi",
    output_dir="./audio/filtered",
    target_videos=100,
    filters=filters,
    audio_format="mp3",
    transcript_lang="hi",
)
```

---

## Requirements

- Python >= 3.9
- [ffmpeg](https://ffmpeg.org/download.html) — required for WAV/MP3 conversion
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — installed automatically via `pip` (see `requirements.txt`)

Install ffmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

## Install

```bash
pip install -e .
```

---

## CLI usage

### Search

Search YouTube and keep downloading until you hit the target count.

```bash
yt-harvest search QUERY OUTPUT_DIR [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target N` | 50 | Stop after **N** successful downloads |
| `--batch-size N` | 100 | Videos fetched per search round |
| `--min-duration SECS` | — | Skip videos shorter than this |
| `--max-duration SECS` | — | Skip videos longer than this |
| `--title-contains WORD …` | — | Title must contain at least one of these |
| `--title-not-contains WORD …` | — | Title must not contain any of these |
| `--format wav\|mp3\|webm` | wav | Audio output format |
| `--lang CODE` | — | Download subtitles in this language (`hi`, `en`, …). Omit to skip. |
| `--rate-limit LIMIT` | 10M | Download speed cap (`10M`, `500K`, …) |
| `--archive FILE` | archive.txt | Tracks downloaded IDs to avoid re-downloading |
| `--no-filter` | — | Disable music/singing/compilation rejection |

**Examples:**

```bash
# Download 30 Hindi podcast videos, 5–30 min, WAV with Hindi subtitles
yt-harvest search "hindi podcast" ./audio \
    --target 30 \
    --min-duration 300 \
    --max-duration 1800 \
    --format wav \
    --lang hi

# Download 100 English interview videos as MP3
yt-harvest search "english interview" ./audio \
    --target 100 \
    --min-duration 600 \
    --format mp3

# Only videos with "episode" or "ep" in the title, excluding "shorts"
yt-harvest search "comedy podcast" ./audio \
    --target 50 \
    --title-contains episode ep \
    --title-not-contains shorts clip promo

# Dry run — see what would match without downloading
yt-harvest search "news analysis" ./audio \
    --min-duration 300 --target 20 --dry-run
```

---

### Channel

Walk a channel's video list, filter, and download all matches.

```bash
yt-harvest channel CHANNEL_URL OUTPUT_DIR [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--min-duration SECS` | — | Skip videos shorter than this |
| `--max-duration SECS` | — | Skip videos longer than this |
| `--type full\|shorts\|both` | full | Which video type to scan |
| `--max-results N` | — | Cap on how many channel videos to inspect. Default: all. |
| `--title-contains WORD …` | — | Title must contain at least one of these |
| `--title-not-contains WORD …` | — | Title must not contain any of these |
| `--format wav\|mp3\|webm` | wav | Audio output format |
| `--lang CODE` | — | Download subtitles in this language (`hi`, `en`, …). Omit to skip. |
| `--rate-limit LIMIT` | 10M | Download speed cap |
| `--archive FILE` | archive.txt | Tracks downloaded IDs to avoid re-downloading |
| `--no-filter` | — | Disable music/singing/compilation rejection |

**Examples:**

```bash
# All 10–60 min videos from a channel, WAV + Hindi subtitles
yt-harvest channel https://www.youtube.com/@SomeChannel ./audio \
    --min-duration 600 \
    --max-duration 3600 \
    --format wav \
    --lang hi

# Shorts only, MP3, no content filters
yt-harvest channel https://www.youtube.com/@SomeChannel ./audio \
    --type shorts \
    --format mp3 \
    --no-filter

# Only scan the first 200 videos, keep those with "vlog" in title
yt-harvest channel https://www.youtube.com/@SomeChannel ./audio \
    --max-results 200 \
    --title-contains vlog
```

---

## Python API

### `search_download`

```python
from yt_harvest import search_download

search_download(
    query="hindi podcast interview",
    output_dir="./audio",
    target_videos=50,
    search_batch_size=100,
    min_duration=300,
    max_duration=1800,
    audio_format="wav",       # "wav" | "mp3" | "webm"
    transcript_lang="hi",     # None = skip subtitles
    rate_limit="10M",
    dry_run=False,
)
```

### `channel_download`

```python
from yt_harvest import channel_download

channel_download(
    channel_url="https://www.youtube.com/@SomeChannel",
    output_dir="./audio",
    min_duration=600,
    max_duration=3600,
    video_type="full",        # "full" | "shorts" | "both"
    max_results=None,         # None = scan entire channel
    audio_format="wav",
    transcript_lang="hi",
    rate_limit="2000",
)
```

### `FilterConfig` — full filter control

```python
from yt_harvest import search_download, FilterConfig

filters = FilterConfig(
    min_duration=300,
    max_duration=1800,
    title_must_contain=["episode", "podcast"],   # ANY match keeps it
    title_must_not_contain=["shorts", "clip"],   # ANY match rejects it
    allowed_langs=["hi"],

    # Content rejections — True by default
    reject_music=True,
    reject_singing=True,
    reject_compilations=True,
    reject_trailers=True,
    reject_reuploads=True,

    # Off by default
    reject_livestreams=False,
    reject_kids_content=False,
    reject_asmr=False,
    reject_multi_speaker=False,

    min_views=1000,
    uploaded_after="20230101",   # YYYYMMDD
)

search_download(
    "hindi podcast",
    "./audio",
    target_videos=100,
    filters=filters,
    audio_format="mp3",
    transcript_lang="hi",
)
```

---

## Output structure

```
audio/
├── archive.txt              ← prevents re-downloading already-seen IDs
└── Channel Name/
    ├── Video Title.wav
    ├── Video Title.hi.vtt   ← subtitle file (when --lang is set)
    └── ...
```
