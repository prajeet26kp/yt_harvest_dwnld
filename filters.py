import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class FilterConfig:
    """
    Configuration for video filtering. Pass to search_download or channel_download
    for fine-grained control. All fields are optional — defaults are sane for
    spoken-word content (rejects music, singing, trailers, compilations, reuploads).

    Duration example:
        FilterConfig(min_duration=120, max_duration=600)  # 2–10 min videos
    """

    # ── Duration ──────────────────────────────────────────────────────────
    min_duration: Optional[int] = None   # seconds; None = no lower bound
    max_duration: Optional[int] = None   # seconds; None = no upper bound

    # ── Video type ────────────────────────────────────────────────────────
    video_type: Optional[str] = None     # "full" | "shorts" | None (both)
    shorts_max_duration: int = 60        # threshold separating shorts from full

    # ── Language ──────────────────────────────────────────────────────────
    allowed_langs: Optional[List[str]] = None          # e.g. ["hi", "en"]
    require_devanagari_title: bool = False

    # ── Content-type rejections (on by default) ───────────────────────────
    reject_music: bool = True
    reject_singing: bool = True
    reject_compilations: bool = True
    reject_trailers: bool = True
    reject_reuploads: bool = True

    # ── Content-type rejections (off by default) ──────────────────────────
    reject_livestreams: bool = False
    reject_kids_content: bool = False
    reject_asmr: bool = False
    reject_multi_speaker: bool = False

    # ── Speech signal ─────────────────────────────────────────────────────
    require_speech_keywords: bool = False
    custom_speech_keywords: Optional[List[str]] = None

    # ── Category lists ────────────────────────────────────────────────────
    allowed_categories: Optional[List[str]] = None
    blocked_categories: Optional[List[str]] = None

    # ── Tag lists ─────────────────────────────────────────────────────────
    required_tags: Optional[List[str]] = None
    blocked_tags: Optional[List[str]] = None
    music_tag_blocklist: Optional[List[str]] = None

    # ── Channel allow/block ───────────────────────────────────────────────
    allowed_channels: Optional[List[str]] = None
    blocked_channels: Optional[List[str]] = None

    # ── Title / description matching ──────────────────────────────────────
    title_must_contain: Optional[List[str]] = None
    title_must_not_contain: Optional[List[str]] = None
    description_must_contain: Optional[List[str]] = None
    description_must_not_contain: Optional[List[str]] = None
    min_title_length: Optional[int] = None

    # ── View counts ───────────────────────────────────────────────────────
    min_views: Optional[int] = None
    max_views: Optional[int] = None

    # ── Upload date (YYYYMMDD strings) ────────────────────────────────────
    uploaded_after: Optional[str] = None
    uploaded_before: Optional[str] = None


def filter_videos(records, config: FilterConfig = None, return_rejected: bool = False):
    """
    Filter a list of video metadata records against a FilterConfig.

    Returns:
        list of passed records, or (passed, rejected) if return_rejected=True.
        rejected is a list of (record, reason_str) tuples.
    """
    if config is None:
        config = FilterConfig()

    passed = []
    rejected = []

    for record in records:
        ok, reason = _apply_all(record, config)
        if ok:
            passed.append(record)
        else:
            rejected.append((record, reason))

    if return_rejected:
        return passed, rejected
    return passed


# ── core filter logic ────────────────────────────────────────────────────

def _apply_all(record, cfg: FilterConfig):
    title       = (record.get("title") or "").lower()
    desc        = (record.get("description") or "").lower()
    dur         = record.get("duration") or 0
    views       = record.get("view_count") or 0
    cats        = _parse_json(record.get("categories", "[]"))
    tags        = _parse_json(record.get("tags", "[]"))
    tags_lower  = {t.lower() for t in tags}
    upload_date = record.get("upload_date") or ""
    channel     = (record.get("channel") or "").lower()
    channel_url = (record.get("channel_url") or "").lower()

    # language
    if cfg.allowed_langs:
        if not _check_language(record, cfg.allowed_langs):
            return False, "language_mismatch"

    if cfg.require_devanagari_title:
        if not _has_devanagari(record.get("title", "")):
            return False, "no_devanagari_in_title"

    # duration
    if cfg.min_duration is not None and dur < cfg.min_duration:
        return False, f"too_short_{dur}s"

    if cfg.max_duration is not None and dur > cfg.max_duration:
        return False, f"too_long_{dur}s"

    # video type
    if cfg.video_type:
        cutoff = cfg.shorts_max_duration
        if cfg.video_type == "shorts" and dur > cutoff:
            return False, "not_a_short"
        if cfg.video_type == "full" and dur <= cutoff:
            return False, "is_a_short"

    # categories
    if cfg.blocked_categories:
        if any(c in cfg.blocked_categories for c in cats):
            return False, "blocked_category"

    if cfg.allowed_categories:
        if not any(c in cfg.allowed_categories for c in cats):
            return False, "category_not_allowed"

    # music
    if cfg.reject_music:
        if "Music" in cats:
            return False, "music_category"
        default_music_tags = {
            "song", "music", "music video", "ost", "soundtrack",
            "lyric", "lyrics", "singing", "singer", "gana", "gaana",
            "remix", "unplugged", "karaoke", "cover song",
        }
        extra = {t.lower() for t in (cfg.music_tag_blocklist or [])}
        if tags_lower & (default_music_tags | extra):
            return False, "music_tags"

    if cfg.reject_singing:
        if _has_singing_patterns(title, desc):
            return False, "singing_content"

    # speech keywords
    if cfg.require_speech_keywords:
        if not _has_speech_signal(title, tags_lower, cfg.custom_speech_keywords):
            return False, "no_speech_signal"

    # tags
    if cfg.required_tags:
        if not (tags_lower & {t.lower() for t in cfg.required_tags}):
            return False, "missing_required_tags"

    if cfg.blocked_tags:
        if tags_lower & {t.lower() for t in cfg.blocked_tags}:
            return False, "blocked_tag"

    # title patterns
    if cfg.title_must_contain:
        if not _matches_any(title, cfg.title_must_contain):
            return False, "title_missing_pattern"

    if cfg.title_must_not_contain:
        if _matches_any(title, cfg.title_must_not_contain):
            return False, "title_blocked_pattern"

    # channel allow/block
    if cfg.allowed_channels:
        allowed_lower = {c.lower() for c in cfg.allowed_channels}
        if channel not in allowed_lower and channel_url not in allowed_lower:
            return False, "channel_not_allowed"

    if cfg.blocked_channels:
        blocked_lower = {c.lower() for c in cfg.blocked_channels}
        if channel in blocked_lower or channel_url in blocked_lower:
            return False, "channel_blocked"

    # upload date
    if cfg.uploaded_after and upload_date and upload_date < cfg.uploaded_after:
        return False, "too_old"

    if cfg.uploaded_before and upload_date and upload_date > cfg.uploaded_before:
        return False, "too_recent"

    # views
    if cfg.min_views is not None and views < cfg.min_views:
        return False, f"too_few_views_{views}"

    if cfg.max_views is not None and views > cfg.max_views:
        return False, f"too_many_views_{views}"

    # description
    if cfg.description_must_contain:
        if not any(t.lower() in desc for t in cfg.description_must_contain):
            return False, "description_missing_term"

    if cfg.description_must_not_contain:
        if any(t.lower() in desc for t in cfg.description_must_not_contain):
            return False, "description_blocked_term"

    # title length
    if cfg.min_title_length is not None:
        if len(record.get("title", "").strip()) < cfg.min_title_length:
            return False, "title_too_short"

    # compilations / trailers / etc.
    if cfg.reject_compilations and _is_compilation(title, desc):
        return False, "compilation"

    if cfg.reject_trailers and _is_trailer(title, dur):
        return False, "trailer_or_teaser"

    if cfg.reject_livestreams and _is_livestream(record, title, tags_lower):
        return False, "livestream"

    if cfg.reject_kids_content and _is_kids_content(title, tags_lower, desc):
        return False, "kids_content"

    if cfg.reject_asmr and _is_asmr(title, tags_lower):
        return False, "asmr"

    if cfg.reject_multi_speaker and _is_multi_speaker(title, desc):
        return False, "multi_speaker"

    if cfg.reject_reuploads and _is_reupload(title, desc):
        return False, "reupload"

    return True, None


# ── content classifiers ───────────────────────────────────────────────────

def _check_language(record, allowed_langs):
    vid_lang = (record.get("language") or "").strip().lower()
    if vid_lang and vid_lang in allowed_langs:
        return True
    # Devanagari title is a reliable Hindi signal
    if "hi" in allowed_langs and _has_devanagari(record.get("title", "")):
        return True
    return False


def _has_singing_patterns(title, desc):
    text = f"{title} {desc}"
    patterns = [
        r"\bofficial\s+(music\s+)?video\b", r"\bfull\s+(video\s+)?song\b",
        r"\blyrical\b", r"\bofficial\s+audio\b", r"\bjukebox\b",
        r"\bsong\s+promo\b", r"\btitle\s+track\b", r"\bstatus\s+video\b",
        r"\bplayback\s+singer\b", r"\bromantic\s+song\b", r"\bsad\s+song\b",
        r"\bparty\s+song\b", r"\bitem\s+song\b", r"\bsufi\s+song\b",
        r"\bqawwali\b", r"\bghazal\b", r"\bbhajan\b", r"\bkirtan\b", r"\baarti\b",
    ]
    return any(re.search(p, text) for p in patterns)


def _has_speech_signal(title, tags_lower, custom_keywords=None):
    text = f"{title} {' '.join(tags_lower)}"
    keywords = [
        "interview", "podcast", "speech", "talk", "discussion",
        "debate", "commentary", "review", "reaction", "vlog",
        "lecture", "explain", "analysis", "story", "monologue",
        "standup", "stand-up", "prank call", "news", "opinion",
        "roast", "rant", "storytime", "qna", "q&a",
        # Hindi speech signals
        "बातचीत", "साक्षात्कार", "भाषण", "चर्चा", "समीक्षा",
    ]
    if custom_keywords:
        keywords.extend(custom_keywords)
    return any(kw in text for kw in keywords)


def _is_compilation(title, desc):
    patterns = [
        r"\bbest\s+of\b", r"\btop\s+\d+\b", r"\bcompilation\b",
        r"\bmashup\b", r"\bmegamix\b", r"\bnon[\s-]?stop\b",
        r"\b\d+\s+hours?\s+of\b", r"\bcollection\b", r"\ball\s+episodes?\b",
    ]
    return any(re.search(p, f"{title} {desc}") for p in patterns)


def _is_trailer(title, duration):
    # Only flag as trailer if it's short (< 5 min) AND has trailer-type keywords
    if duration > 300:
        return False
    patterns = [
        r"\btrailer\b", r"\bteaser\b", r"\bpromo\b",
        r"\bcoming\s+soon\b", r"\bfirst\s+look\b", r"\bsneak\s+peek\b",
    ]
    return any(re.search(p, title) for p in patterns)


def _is_livestream(record, title, tags_lower):
    if record.get("is_live") or record.get("was_live"):
        return True
    if any(re.search(p, title) for p in [r"\blive\s+stream\b", r"\blivestream\b"]):
        return True
    return "livestream" in tags_lower or "live stream" in tags_lower


def _is_kids_content(title, tags_lower, desc):
    signals = {
        "nursery rhyme", "nursery rhymes", "kids song", "kids songs",
        "children song", "baby song", "toddler", "cocomelon",
        "chu chu tv", "infobells", "kids tv", "बच्चों के गाने", "लोरी",
    }
    text = f"{title} {' '.join(tags_lower)} {desc}"
    return any(s in text for s in signals)


def _is_asmr(title, tags_lower):
    return "asmr" in title or "asmr" in tags_lower


def _is_multi_speaker(title, desc):
    patterns = [
        r"\broundtable\b", r"\bpanel\s+discussion\b",
        r"\b\d+\s+people\b", r"\bgroup\s+discussion\b", r"\btown\s+hall\b",
    ]
    return any(re.search(p, f"{title} {desc}") for p in patterns)


def _is_reupload(title, desc):
    patterns = [
        r"\breupload\b", r"\bre[\s-]?upload\b", r"\bcredits?\s+to\b",
        r"\bnot\s+mine\b", r"\bnot\s+my\s+(video|content)\b",
        r"\ball\s+rights?\s+(belong|go)\b", r"\bno\s+copyright\s+infringement\b",
        r"\bi\s+don'?t\s+own\b",
    ]
    return any(re.search(p, f"{title} {desc}") for p in patterns)


# ── helpers ───────────────────────────────────────────────────────────────

def _parse_json(value):
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _has_devanagari(text):
    return bool(re.search(r"[\u0900-\u097F]", text))


def _matches_any(text, patterns):
    for p in patterns:
        if isinstance(p, str):
            if p.lower() in text:
                return True
        else:
            if re.search(p, text):
                return True
    return False
