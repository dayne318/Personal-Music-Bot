import yt_dlp
import discord

# Shared queues and volumes across guilds
queues = {}
volumes = {}

def search_youtube(query):
    """Search YouTube and return first video URL and title"""
    ydl_opts = {
        'quiet': False,
        'format': 'bestaudio/best',
        'default_search': 'ytsearch',
        'noplaylist': True,
        'skip_download': True,
        'extract_flat': True,
        'force_generic_extractor': False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
                return entry.get('url'), entry.get('title')
        except Exception as e:
            print(f"Search error: {e}")
    return None, None

def get_audio_source(url, ctx):
    """Download and return FFmpeg audio source with volume"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'audio',
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    volume_level = volumes.get(ctx.guild.id, 0.5)
    return discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("audio.mp3"), volume=volume_level)
