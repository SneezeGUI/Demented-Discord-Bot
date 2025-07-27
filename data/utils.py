# C:/Development/Projects/Demented-Discord-Bot/data/utils.py

import os
import json
import logging
import random
import discord
from discord.ext import commands
from typing import Dict, Any, Optional, Union

logger = logging.getLogger('demented_bot.utils')


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file. This is now only called once at startup."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded successfully from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {e}")
        return {}


def get_config_value(bot: commands.Bot, key: str, default: Any = None) -> Any:
    """Get a configuration value by key with optional dot notation from the bot's config."""
    config = bot.config
    if '.' in key:
        parts = key.split('.')
        value = config
        try:
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    return config.get(key, default)


def create_embed(
        bot: commands.Bot,
        title: str = "",
        description: str = "",
        color: Optional[Union[discord.Color, int, str]] = None,
        fields: list = None,
        footer: str = None,
        thumbnail_url: str = None,
        image_url: str = None,
        author_name: str = None,
        author_icon_url: str = None
) -> discord.Embed:
    """Create a Discord embed with consistent styling."""

    COLOR_MAP = {
        "error": "ERROR_COLOR",
        "success": "SUCCESS_COLOR",
        "warning": "WARNING_COLOR",
        "default": "DEFAULT_COLOR"
    }

    final_color_val = 0x7289DA  # Fallback default

    if isinstance(color, str):
        color_lower = color.lower()
        if color_lower in COLOR_MAP:
            config_key = COLOR_MAP[color_lower]
            default_hex = get_config_value(bot, f"FALLBACKS.{config_key}", "0x7289DA")
            color_value = get_config_value(bot, config_key, default_hex)
            final_color_val = int(color_value, 16)
        elif color.startswith("0x"):
            try:
                final_color_val = int(color, 16)
            except ValueError:
                logger.warning(f"Invalid hex color format: {color}")
    elif isinstance(color, (discord.Color, int)):
        final_color_val = color
    else:  # Handles None or other types
        default_hex = get_config_value(bot, "DEFAULT_COLOR", "0x7289DA")
        final_color_val = int(default_hex, 16)

    embed = discord.Embed(title=title, description=description, color=final_color_val)

    if fields:
        for field in fields:
            name, value, inline = (field if len(field) == 3 else (field[0], field[1], False))
            embed.add_field(name=name, value=value, inline=inline)

    if footer:
        embed.set_footer(text=footer)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if image_url:
        embed.set_image(url=image_url)
    if author_name:
        embed.set_author(name=author_name, icon_url=author_icon_url)

    return embed


def get_random_sound_file():
    """Get a random sound file from the bot_sounds directory."""
    sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot_sounds')
    if not os.path.exists(sounds_dir):
        logger.error(f"Sound directory not found: {sounds_dir}")
        return None
    sound_files = [f for f in os.listdir(sounds_dir) if f.endswith(('.mp3', '.wav'))]
    if not sound_files:
        logger.warning(f"No sound files found in {sounds_dir}")
        return None
    return os.path.join(sounds_dir, random.choice(sound_files))