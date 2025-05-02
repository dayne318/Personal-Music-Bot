# bot.py
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")  # Get the bot token from environment variable

# Set up the required Discord intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent to read user messages

# Create a bot instance with a command prefix
bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_ready():
    # This event is called when the bot has connected to Discord successfully
    print(f"Bot is online as {bot.user}")

async def main():
    # Load the music command extension from a separate file
    await bot.load_extension("music_cog")
    # Start the bot using the token
    await bot.start(TOKEN)

# Run the main async function
asyncio.run(main())