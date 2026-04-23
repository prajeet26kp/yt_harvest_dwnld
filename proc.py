from yt_harvest_dwnld import search_download, channel_download, FilterConfig




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
