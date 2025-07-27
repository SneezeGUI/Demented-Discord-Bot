# C:/Development/Projects/Demented-Discord-Bot/data/helper_functions.py

import asyncio
import random
import logging
import discord
import functools
from datetime import datetime
from discord.ext import commands
from data.session_manager import cached_http_get
from data.utils import create_embed, get_config_value

logger = logging.getLogger('demented_bot.helpers')


async def get_joke(bot: commands.Bot, category="Dark"):
    """Get a joke from the API - shared implementation."""
    joke_api_timeout = get_config_value(bot, "API_TIMEOUTS.JOKE_API", 10)

    category = category.capitalize()
    valid_categories = ["Programming", "Misc", "Dark", "Spooky", "Christmas", "Any"]
    if category not in valid_categories:
        category = "Any"

    url = f"https://v2.jokeapi.dev/joke/{category}"

    # CORRECTED: Removed the invalid 'response_type' argument
    data = await cached_http_get(url, ttl_seconds=3600, timeout=joke_api_timeout)

    if not data:
        fallback_jokes = [
            (False, "Why do programmers prefer dark mode? Because light attracts bugs.", None, None),
            (True, None, "What do you call a programmer from Finland?", "Nerdic."),
            (True, None, "What's a programmer's favorite hangout place?", "Foo Bar.")
        ]
        is_twopart, joke_text, setup, delivery = random.choice(fallback_jokes)
        return joke_text, is_twopart, setup, delivery

    if data.get('type') == 'twopart':
        setup = data.get('setup', "No setup found")
        delivery = data.get('delivery', "No punchline found")
        return None, True, setup, delivery
    else:
        joke_text = data.get('joke', "No joke found")
        return joke_text, False, None, None


async def get_bored_activity(participants=1):
    """Get a random activity suggestion from BoredAPI."""
    participants = max(1, min(10, int(participants)))
    url = "http://www.boredapi.com/api/activity"
    params = {"participants": participants}

    # CORRECTED: Removed the invalid 'response_type' argument
    data = await cached_http_get(url, params=params, ttl_seconds=300)

    if not data:
        fallback_activities = [
            {"activity": "Learn a new programming language", "type": "education", "price": 0.0, "accessibility": 0.1},
            {"activity": "Start a book club", "type": "social", "price": 0.1, "accessibility": 0.2},
            {"activity": "Go for a walk in nature", "type": "recreational", "price": 0.0, "accessibility": 0.0}
        ]
        return random.choice(fallback_activities)

    return data


async def create_temporary_message(ctx_or_interaction, content=None, embed=None, delete_after=5, ephemeral=False):
    """Create a message that auto-deletes after a specified time."""
    try:
        if isinstance(ctx_or_interaction, discord.Interaction):
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
                if not ephemeral and delete_after > 0:
                    original_response = await ctx_or_interaction.original_response()
                    await asyncio.sleep(delete_after)
                    try:
                        await original_response.delete()
                    except discord.NotFound:
                        pass
                return await ctx_or_interaction.original_response()
            else:
                followup = await ctx_or_interaction.followup.send(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
                if not ephemeral and delete_after > 0:
                    await asyncio.sleep(delete_after)
                    try:
                        await followup.delete()
                    except discord.NotFound:
                        pass
                return followup
        else:
            return await ctx_or_interaction.send(content=content, embed=embed, delete_after=delete_after)
    except Exception as e:
        logger.error(f"Error creating temporary message: {e}")
        return None


def timed_command(description="Command execution"):
    """Decorator to time command execution and log performance."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"{description}: {execution_time:.2f}ms")
            return result
        return wrapper
    return decorator


async def schedule_voice_disconnect(voice_client, delay=5):
    """Schedule disconnection from voice channel after delay."""
    try:
        await asyncio.sleep(delay)
        if voice_client and voice_client.is_connected() and not voice_client.is_playing():
            await voice_client.disconnect()
            logger.info(f"Automatically disconnected from voice channel after {delay}s")
    except Exception as e:
        logger.error(f"Error in scheduled disconnect: {e}")


class GameData:
    """Simple lazy-loading for game data files."""
    _data = {}

    @classmethod
    def get(cls, game_type):
        """Get game data, loading it only if needed."""
        import os
        if game_type in cls._data:
            return cls._data[game_type]

        file_path = f"data/{game_type}.txt"

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cls._data[game_type] = [line.strip() for line in f if line.strip()]
                logger.info(f"Loaded {len(cls._data[game_type])} items for {game_type}")
            except Exception as e:
                logger.error(f"Error loading game data for '{game_type}': {e}")
                cls._data[game_type] = []
        else:
            logger.warning(f"Game data file not found: {file_path}")
            cls._data[game_type] = []

        return cls._data[game_type]