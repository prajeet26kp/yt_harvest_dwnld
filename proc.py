
from yt_harvest_dwnld import search_download, channel_download, FilterConfig


channel_download(
    channel_url="https://www.youtube.com/@AmazonMXPlayer",
    output_dir="./audio/channel",
    min_duration=600,       # 10 min
    max_duration=3600,      # "full" | "shorts" | "both"
    audio_format="wav",
    transcript_lang="hi",
    rate_limit="10M",
)

