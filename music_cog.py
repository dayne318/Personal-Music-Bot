import discord
from discord.ext import commands
from utils import search_youtube, get_audio_source, volumes, queues

import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def play_next(self, ctx):
        """Play the next song in the queue or disconnect if queue is empty."""
        if ctx.guild.id in queues and queues[ctx.guild.id]:
            next_url, next_title = queues[ctx.guild.id].pop(0)
            source = get_audio_source(next_url, ctx)

            def after_callback(error):
                if error:
                    print(f"Error in play_next: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            ctx.voice_client.play(source, after=after_callback)
            await ctx.send(f"🎵 Now playing: {next_title}")
        else:
            # Leave if no audio is played in 3 min.
            await asyncio.sleep(180)

            if not ctx.voice_client.is_playing() and (ctx.guild.id not in queues or not queues[ctx.guild.id]):
                await ctx.send("🎵 Queue is empty, leaving voice channel.")
                await ctx.voice_client.disconnect()
                queues.pop(ctx.guild.id, None)

    @commands.command()
    async def join(self, ctx):
        """Join the user's voice channel"""
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await ctx.send(f"Joined {ctx.author.voice.channel.name}!")
        else:
            await ctx.send("You need to be in a voice channel first!")

    @commands.command()
    async def play(self, ctx, *, query: str):
        """Plays audio from a YouTube URL or search query"""
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You need to be in a voice channel!")
                return

        youtube_url = query if "youtube.com" in query or "youtu.be" in query else None
        if not youtube_url:
            await ctx.send(f"🔍 Searching for: {query}...")
            url, title = search_youtube(query)
            if not url:
                await ctx.send("❌ No results found.")
                return
            # await ctx.send(f"✅ Found: {title}")
        else:
            url = query
            title = "YouTube URL provided"

        if ctx.voice_client.is_playing():
            queues.setdefault(ctx.guild.id, []).append((url, title))
            await ctx.send(f"🎵 Added to queue: {title}")
        else:
            queues[ctx.guild.id] = []
            try:
                source = get_audio_source(url, ctx)
            except ValueError as ve:
                await ctx.send(f"❌ {ve}")
                return
            except Exception as e:
                await ctx.send(f"❌ Error: {e}")
                return

            def after_callback(error):
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            ctx.voice_client.play(source, after=after_callback)
            await ctx.send(f"🎵 Now playing: {title}")

    @commands.command()
    async def queue(self, ctx):
        """Displays the current song queue"""
        if ctx.guild.id in queues and queues[ctx.guild.id]:
            queue_list = "\n".join([f"🎵 {title}" for _, title in queues[ctx.guild.id]])
            await ctx.send(f"📜 **Song Queue:**\n{queue_list}")
        else:
            await ctx.send("🎵 The queue is empty!")

    @commands.command()
    async def skip(self, ctx):
        """Skips the currently playing song"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭️ Skipping to next song...")
        else:
            await ctx.send("❌ No song is currently playing.")

    @commands.command()
    async def stop(self, ctx):
        """Stops playback and clears the queue"""
        if ctx.voice_client:
            ctx.voice_client.stop()
            queues.pop(ctx.guild.id, None)
            await ctx.send("⏹️ Stopped playback and cleared queue.")
        else:
            await ctx.send("❌ No audio is playing.")

    @commands.command()
    async def leave(self, ctx):
        """Leaves the voice channel"""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            queues.pop(ctx.guild.id, None)
            await ctx.send("👋 Disconnected.")
        else:
            await ctx.send("❌ Not in a voice channel.")

    @commands.command()
    async def pause(self, ctx):
        """Pauses audio"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Paused.")
        else:
            await ctx.send("❌ Nothing playing.")

    @commands.command()
    async def resume(self, ctx):
        """Resumes paused audio"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Resumed.")
        else:
            await ctx.send("❌ Nothing paused.")

    @commands.command()
    async def volume(self, ctx, level: int = None):
        """Get the current volume"""
        guild_id = ctx.guild.id

        if level is None:
            current_volume = volume.get(guild_id, 0.5)
            await ctx.send(f"🔊 Current volume is set to {int(current_volume * 100)}%")
            return


        """Sets the volume 1–100"""
        if ctx.voice_client and ctx.voice_client.source:
            if 1 <= level <= 100:
                volumes[ctx.guild.id] = level / 100
                ctx.voice_client.source.volume = volumes[ctx.guild.id]
                await ctx.send(f"🔊 Volume set to {level}%")
            else:
                await ctx.send("❌ Volume must be 1–100.")
        else:
            await ctx.send("❌ No audio is currently playing.")

async def setup(bot):
    await bot.add_cog(Music(bot))
