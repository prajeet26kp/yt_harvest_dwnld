from yt_harvest_dwnld import search_download, channel_download, FilterConfig


channel_download(
    channel_url="https://www.youtube.com/@AmazonMXPlayer",
    output_dir="./audio/channel",
    min_duration=1200,  
    max_results=50, 
    max_downloads=20,
    audio_format="wav",
    transcript_lang="hi",
    rate_limit="2000",
    filters=FilterConfig(
          title_must_contain=["Episode"],                                                                                                                
      ),                                                                                                                                                                                               
)