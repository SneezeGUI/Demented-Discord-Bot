# C:/Development/Projects/Demented-Discord-Bot/cogs/events.py

import random
import logging
import discord
import re
import os
import asyncio
import json
import glob
from pathlib import Path
from discord.ext import commands

from data.utils import get_config_value
from data.database_manager import get_server_config_value

# --- gTTS for Text-to-Speech ---
try:
    from gtts import gTTS

    gtts_available = True
except ImportError:
    gtts_available = False

logger = logging.getLogger('demented_bot.events')


# --- Helper function to get FFmpeg path with precedence ---
def get_ffmpeg_executable(bot_instance) -> str:
    """
    Gets the FFmpeg executable path with a clear order of precedence:
    1. Explicit path from config.json (most reliable for services).
    2. Dynamic search for a winget installation.
    3. Fallback to 'ffmpeg' assuming it's in the system PATH.
    """
    # 1. Check for an explicit path in the config file.
    config_path = get_config_value(bot_instance, "FFMPEG_PATH", None)
    if config_path and os.path.exists(config_path):
        logger.info(f"Using explicit FFmpeg path from config: {config_path}")
        return config_path

    # 2. If no config path, try to find the winget installation path.
    try:
        home_dir = os.path.expanduser('~')
        search_pattern = os.path.join(
            home_dir, 'AppData', 'Local', 'Microsoft', 'WinGet', 'Packages',
            'Gyan.FFmpeg.Essentials*',
            'ffmpeg-*-essentials_build',
            'bin',
            'ffmpeg.exe'
        )
        results = glob.glob(search_pattern)
        if results:
            found_path = results[0]
            logger.info(f"Dynamically found winget FFmpeg executable at: {found_path}")
            return found_path
    except Exception as e:
        logger.warning(f"Could not dynamically search for winget FFmpeg. Error: {e}")

    # 3. If all else fails, fall back to the default.
    logger.info("No explicit or winget FFmpeg path found, falling back to 'ffmpeg' in system PATH.")
    return 'ffmpeg'


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rng_threshold = get_config_value(self.bot, 'RNG_THRESHOLD', 20)
        self.random_responses_enabled = get_config_value(self.bot, "FEATURES.RANDOM_RESPONSES", True)
        self._bot_name_trigger = None

        # Find and store the FFmpeg path on startup
        self.ffmpeg_executable_path = get_ffmpeg_executable(self.bot)

        self.tts_cache_path = Path(__file__).parent.parent / "data" / "tts_cache"
        self.sounds_path = Path(__file__).parent.parent / "data" / "bot_sounds"
        self.tts_cache_path.mkdir(exist_ok=True)
        self.sounds_path.mkdir(exist_ok=True)
        if not gtts_available:
            logger.warning("`gTTS` not found. AI voice features will be disabled. Install with: pip install gTTS")

    @property
    def bot_name_trigger(self) -> str:
        if self._bot_name_trigger is None and self.bot.user:
            self._bot_name_trigger = self.bot.user.name.split()[0].lower()
            logger.info(f"Bot name trigger word set to: '{self._bot_name_trigger}'")
        return self._bot_name_trigger or ""

    async def _play_and_cleanup(self, voice_client: discord.VoiceClient, source_path: Path, is_tts: bool):
        """Plays an audio file and handles cleanup afterwards."""

        def after_playing(error):
            if error:
                logger.error(f'Error playing file {source_path}: {error}')
            if is_tts:
                try:
                    os.remove(source_path)
                    logger.info(f"Cleaned up TTS file: {source_path}")
                except OSError as e:
                    logger.error(f"Error deleting TTS file {source_path}: {e}")
            coro = voice_client.disconnect()
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result(timeout=5)
            except Exception as e:
                logger.error(f"Error during voice client disconnect: {e}")

        source = discord.FFmpegPCMAudio(
            str(source_path),
            executable=self.ffmpeg_executable_path
        )
        voice_client.play(source, after=after_playing)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # --- Channel Restriction Check ---
        raw_restricted = get_server_config_value(message.guild.id, "restricted_channels")
        restricted_ids = json.loads(raw_restricted) if raw_restricted else []
        if message.channel.id in restricted_ids:
            return

        ai_enabled = get_config_value(self.bot, "AI_SETTINGS.ENABLED", False)
        if not ai_enabled:
            return

        is_direct_mention = self.bot.user.mentioned_in(message)
        trigger_word = self.bot_name_trigger
        is_name_mention = False
        if trigger_word and re.search(r'\b' + re.escape(trigger_word) + r'\b', message.content, re.IGNORECASE):
            is_name_mention = True

        is_reply_to_bot = False
        if message.reference and message.reference.message_id:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.author == self.bot.user:
                    is_reply_to_bot = True
            except discord.NotFound:
                logger.warning(f"Could not fetch replied-to message ID {message.reference.message_id}")

        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            logger.error("AI Cog not found, cannot process messages.")
            return

        if (is_direct_mention or is_name_mention) and 'join' in message.content.lower():
            if not message.author.voice or not message.author.voice.channel:
                await message.reply("You need to be in a voice channel for me to join.", mention_author=False)
                return
            if message.guild.voice_client:
                await message.reply("I'm already in a voice channel here, you goof.", mention_author=False)
                return
            voice_channel = message.author.voice.channel

            # --- MODIFICATION: More robust connection handling ---
            voice_client = None
            try:
                # The timeout here is for the entire connection process, including internal retries.
                voice_client = await voice_channel.connect(timeout=20.0)
            except asyncio.TimeoutError:
                logger.error(f"Connection to voice channel {voice_channel.id} timed out after multiple retries.")
                # Check bot permissions as a possible cause for failure.
                bot_member = voice_channel.guild.me
                vc_perms = voice_channel.permissions_for(bot_member)
                if not vc_perms.connect:
                    error_msg = "I tried to connect, but I don't have the **Connect** permission for that voice channel."
                elif not vc_perms.speak:
                    error_msg = "I can connect, but I don't have the **Speak** permission, so I won't join."
                else:
                    error_msg = "I tried to connect, but it timed out. This could be a temporary Discord issue or a network problem. Please try again in a moment."
                await message.reply(error_msg, mention_author=False)
                return
            except discord.Forbidden:
                logger.error(f"Forbidden to connect to voice channel {voice_channel.id}.")
                await message.reply("I don't have the required permissions to join that voice channel.", mention_author=False)
                return
            except Exception as e:
                logger.error(f"An unexpected error occurred while connecting to voice channel {voice_channel.id}: {e}", exc_info=True)
                await message.reply("An unexpected error occurred while I was trying to connect.", mention_author=False)
                return

            # If we reach here, the connection is successful.
            if gtts_available:
                async with message.channel.typing():
                    greeting_text = await ai_cog.get_voice_greeting(message.author.display_name)
                    tts = gTTS(text=greeting_text, lang='en', slow=False)
                    file_path = self.tts_cache_path / f"voice_{message.guild.id}_{discord.utils.utcnow().timestamp()}.mp3"
                    await self.bot.loop.run_in_executor(None, tts.save, str(file_path))
                    await self._play_and_cleanup(voice_client, file_path, is_tts=True)
            else:
                await message.reply("My voice box is broken (gTTS library not found). I can't speak right now.",
                                    mention_author=False)
                await voice_client.disconnect()
            return
            # --- END MODIFICATION ---

        # --- Centralized conversational logic with proactive learning ---
        if is_direct_mention or is_name_mention or is_reply_to_bot:
            # Get all mentioned members, excluding bots.
            mentioned_members = [m for m in message.mentions if not m.bot]

            async with message.channel.typing():
                # --- Proactive Fact Assessment ---
                fact_confirmation = None
                # Give it a 25% chance to try and learn something new from the conversation
                if random.randint(1, 100) <= 25:
                    fact_confirmation = await ai_cog.assess_and_remember_fact(message)
                # --- End Fact Assessment ---

                # Pass the message and the list of mentioned users to the AI for the main response
                response_data = await ai_cog.get_conversational_response(
                    message,
                    mentioned_users=mentioned_members
                )

                if response_data and response_data.get("response_text"):
                    final_text = response_data["response_text"]
                    users_to_tag = response_data.get("users_to_tag", [])

                    # Build a dictionary to easily find member objects by their display name
                    taggable_users = {str(message.author.display_name): message.author}
                    for member in mentioned_members:
                        taggable_users[str(member.display_name)] = member
                    taggable_users[str(self.bot.user.display_name)] = self.bot.user

                    # Replace placeholder names in the AI's text with actual mentions
                    for name in users_to_tag:
                        if name in taggable_users:
                            # Use regex to replace the name only if it's a whole word
                            final_text = re.sub(r'\b' + re.escape(name) + r'\b', taggable_users[name].mention,
                                                final_text, count=1)

                    # Append the learning confirmation if it exists
                    if fact_confirmation:
                        final_text += f"\n\n*({fact_confirmation})*"

                    await message.reply(final_text, mention_author=False)
            return

        # The random insult logic remains the same
        rng = random.randrange(0, 100)
        if self.random_responses_enabled and rng < self.rng_threshold:
            logger.info(f"RNG trigger for insult on {message.author.name}'s message.")
            async with message.channel.typing():
                insult = await ai_cog.get_insulting_response(message)
                if insult:
                    await message.reply(insult, mention_author=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
