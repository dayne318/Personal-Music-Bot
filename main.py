import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import re

from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup bot command prefix
intents = discord.Intents.default()
intents.message_content = True  # This is REQUIRED for reading messages

bot = commands.Bot(command_prefix="$", intents=intents)

# Dictionary to keep track of voice clients and song queues
queues = {}

def search_youtube(query):
    """Search YouTube -- return first video URL"""
    ydl_opts = {
        'quiet' : False,
        'format': 'bestaudio/best',
        'default_search': 'ytsearch',
        'noplaylist': True,
        'skip_download': True,
        'extract_flat': True,
        'force_generic_extractor': False
    }

    # **Force YouTube search by adding 'ytsearch:' before the query**
    search_query = f"ytsearch:{query}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
            print(f"🔍 Search results: {info}")  # Debugging output

            if 'entries' in info and len(info['entries']) > 0:
                first_entry = info['entries'][0]
                if 'url' in first_entry:
                    return first_entry['url'], first_entry['title']
        except Exception as e:
            print(f"Error during YouTube search: {e}")  # Debugging info

    return None, None  # Return None if no results found

# Function to get YouTube audio stream
def get_audio_source(url, ctx):
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

    # Default volume to 50% if not set
    volume_level = volumes.get(ctx.guild.id, 0.5)

    return discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("audio.mp3"), volume=volume_level)

async def play_next(ctx):
    """Play the next song in the queue or disconnect if queue is empty."""
    if ctx.guild.id in queues and queues[ctx.guild.id]:  
        next_url, next_title = queues[ctx.guild.id].pop(0)  # Take next song  
        source = get_audio_source(next_url, ctx)

        def after_callback(error):
            if error:
                print(f"Error in play_next: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        ctx.voice_client.play(source, after=after_callback)
        await ctx.send(f"🎵 Now playing: {next_title}")
    else:
        await ctx.send("🎵 Queue is empty, leaving voice channel.")
        await ctx.voice_client.disconnect()
        queues.pop(ctx.guild.id, None)  # Ensure the queue is fully cleared

# Join a voice channel
@bot.command()
async def join(ctx):
    """Join the user's voice channel"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f"Joined {channel.name}!")
    else:
        await ctx.send("You need to be in a voice channel first!")

# Play a YouTube video’s audio
@bot.command()
async def play(ctx, *, query: str):
    """Plays audio from a YouTube URL or search query"""
    if not ctx.voice_client:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            await ctx.send("You need to be in a voice channel!")
            return

    # Check if the query is a YouTube URL
    youtube_url_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+')
    if youtube_url_pattern.match(query):
        url = query  # Use the given URL directly
        title = "YouTube URL provided"
    else:
        url, title = search_youtube(query)
        if not url:
            await ctx.send("❌ No results found.")
            return
        await ctx.send(f"✅ Found: {title}")

    # Handle queue or immediate play
    if ctx.voice_client.is_playing():
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append((url, title))
        await ctx.send(f"🎵 Added to queue: {title}")
    else:
        # If bot was stuck from previous queue issue, **clear it before playing new song**
        queues[ctx.guild.id] = []
        source = get_audio_source(url, ctx)

        def after_callback(error):
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        ctx.voice_client.play(source, after=after_callback)
        await ctx.send(f"🎵 Now playing: {title}")

@bot.command()
async def queue(ctx):
    """Displays the current song queue"""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = "\n".join([f"🎵 {title}" for _, title in queues[ctx.guild.id]])
        await ctx.send(f"📜 **Song Queue:**\n{queue_list}")
    else:
        await ctx.send("🎵 The queue is empty!")    

@bot.command()
async def skip(ctx):
    """Skips the currently playing song and plays the next song in the queue."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()  # Stop current song
        await ctx.send("⏭️ Skipping to next song...") 
    else:
        await ctx.send("❌ No song is currently playing.")

#Stop the bot
@bot.command()
async def stop(ctx):
    """Stops playback and clears the audio queue."""
    if ctx.voice_client:
        ctx.voice_client.stop()
        queues.pop(ctx.guild.id, None)  # Safe way to clear queue
        await ctx.send("⏹️ Stopped playback and cleared queue.")
    else:
        await ctx.send("❌ No audio is playing.")

@bot.command()
async def leave(ctx):
    """Disconnects the bot from the voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        queues.pop(ctx.guild.id, None)
        await ctx.send("👋 Disconnected from the voice channel.")
    else:
        await ctx.send("I'm not in a voice channel.")

@bot.command()
async def test(ctx):
    if ctx.voice_client:
        source = discord.FFmpegPCMAudio("test.mp3", executable="ffmpeg", options="-vn")
        ctx.voice_client.play(source)
        await ctx.send("Playing test audio.")

@bot.command()
async def pause(ctx):
    """Pauses the currently playing audio"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused playback.")
    else:
        await ctx.send("No audio is playing right now.")

@bot.command()
async def resume(ctx):
    """Resumes the paused audio"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed playback.")
    else:
        await ctx.send("There's no paused audio to resume.")


volumes = {}

@bot.command()
async def volume(ctx, level: int):
    """Set the volume of the bot (1-100)"""
    if ctx.voice_client and ctx.voice_client.source:
        if 1 <= level <= 100:
            volumes[ctx.guild.id] = level / 100  # Normalize to 0.0 - 1.0
            ctx.voice_client.source.volume = volumes[ctx.guild.id]
            await ctx.send(f"🔊 Volume set to {level}%")
        else:
            await ctx.send("❌ Volume must be between 1 and 100.")
    else:
        await ctx.send("❌ No audio is currently playing.")

# Run the bot with your token
bot.run(TOKEN)
