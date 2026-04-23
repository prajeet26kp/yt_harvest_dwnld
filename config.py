AUDIO_FORMAT = "wav"
TRANSCRIPT_LANG = "hi"
DEFAULT_SEARCH_LANG = "hi"

FORMAT_MAP = {
    "webm": {
        "ydl_format": "bestaudio[ext=webm]/bestaudio/best",
        "ext": "webm",
        "codec": "libopus",
    },
    "mp3": {
        "ydl_format": "bestaudio/best",
        "ext": "mp3",
        "codec": "libmp3lame",
    },
    "wav": {
        "ydl_format": "bestaudio/best",
        "ext": "wav",
        "codec": None,
    },
}
