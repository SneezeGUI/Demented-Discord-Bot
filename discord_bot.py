# C:/Development/Projects/Demented-Discord-Bot/discord_bot.py

"""
Demented Discord Bot - A feature-rich Discord bot using py-cord 2.x
with modern async patterns and app_commands for slash commands.
"""
import os
import sys
import logging
import asyncio
import platform
import time
import random
from typing import Dict, Any, Optional

# --- MODIFICATION: Load environment variables FIRST ---
from dotenv import load_dotenv
load_dotenv()
# --- END MODIFICATION ---

import discord
from discord import app_commands
from discord.ext import commands, tasks

# Now, it's safe to import local modules that depend on .env variables
from data.web_server import keep_alive
from data.session_manager import SessionManager
from data.utils import load_config, create_embed
from data.database_manager import setup_database

# Set up logging with proper format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', 'a', encoding='utf-8')
    ]
)
logger = logging.getLogger('demented_bot')

# Quieten down noisy third-party libraries
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Get bot token and creator ID from environment variables
bot_token = os.getenv('BOT_TOKEN')
creator_id_str = os.getenv('CREATOR_ID')

if not bot_token:
    logger.critical('BOT_TOKEN not found in environment variables!')
    sys.exit('Bot token not provided. Please set the BOT_TOKEN environment variable.')

# Load config once at startup
config = load_config()
BOT_PREFIX = config.get('BOT_PREFIX', '!')

# Initialize bot with comprehensive intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.voice_states = True


# =============================================================================
# Bot Subclass
# =============================================================================

class DementedBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.start_time = discord.utils.utcnow()
        self.loaded_cogs = {}
        self.failed_cogs = {}

        try:
            self.creator_id = int(creator_id_str) if creator_id_str else None
            if self.creator_id:
                logger.info(f"Creator ID loaded: {self.creator_id}")
        except (ValueError, TypeError):
            logger.warning("CREATOR_ID in .env is not a valid integer. Creator-specific features will be disabled.")
            self.creator_id = None

    async def setup_hook(self):
        """This hook is called after login but before connecting to the Gateway."""
        logger.info("Running setup hook...")
        try:
            # Load all cogs before syncing
            await load_cogs()

            # Sync commands to Discord
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed during setup_hook: {e}", exc_info=True)
        logger.info("Setup hook completed")

    async def on_ready(self):
        """Handle bot startup events and set status."""
        guild_count = len(self.guilds)
        member_count = sum(guild.member_count for guild in self.guilds)
        logger.info(f"Bot is online! Connected to {guild_count} guilds with {member_count} members")

        print("\n" + "=" * 50)
        print(f"Bot is online as {self.user.name}")
        print(f"ID: {self.user.id}")
        print(f"Connected to {guild_count} guilds with {member_count} members")

        if self.loaded_cogs:
            print(f"\nSuccessfully loaded {len(self.loaded_cogs)} cogs:")
            for cog_name in self.loaded_cogs:
                print(f"  ✅ {cog_name}")

        if self.failed_cogs:
            print(f"\nFailed to load {len(self.failed_cogs)} cogs:")
            for cog_name, error in self.failed_cogs.items():
                print(f"  ❌ {cog_name}: {error}")

        print("=" * 50 + "\n")


def get_random_activity(cfg: Dict[str, Any]) -> Optional[discord.Activity]:
    """Selects a random activity from the config file."""
    listening_statuses = cfg.get('LISTENING_STATUSES', [])
    playing_statuses = cfg.get('PLAYING_STATUSES', [])

    activities = []
    if listening_statuses:
        activities.extend([(discord.ActivityType.listening, name) for name in listening_statuses])
    if playing_statuses:
        activities.extend([(discord.ActivityType.playing, name) for name in playing_statuses])

    if not activities:
        logger.warning("No statuses found in config file. Bot will have no activity.")
        return None

    activity_type, activity_name = random.choice(activities)
    return discord.Activity(type=activity_type, name=activity_name)


# Instantiate our custom bot
bot = DementedBot(
    command_prefix=commands.when_mentioned_or(BOT_PREFIX),
    intents=intents,
    help_command=None,
    case_insensitive=True,
    activity=get_random_activity(config)
)


# =============================================================================
# Event Handlers
# =============================================================================

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Centralized error handler for all prefix commands."""
    try:
        command_name = ctx.command.name if ctx.command else "unknown"
        error_embed = create_embed(ctx.bot, title="Command Error", color="error")

        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            error_embed.description = f"You missed a required argument: `{error.param.name}`."
        elif isinstance(error, commands.BadArgument):
            error_embed.description = "You provided an invalid argument. Please check the command's help."
        elif isinstance(error, commands.CommandOnCooldown):
            error_embed.description = f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds."
        elif isinstance(error, commands.MissingPermissions):
            error_embed.description = "You don't have the required permissions to run this command."
        else:
            error_embed.description = "An unexpected error occurred while running this command."
            logger.error(f"Unhandled error in command '{command_name}': {error}", exc_info=True)

        await ctx.send(embed=error_embed)
    except Exception as e:
        logger.error(f"Error in on_command_error handler: {e}", exc_info=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Error handler for application commands (slash commands)."""
    try:
        command_name = interaction.command.name if interaction.command else "unknown"
        embed = create_embed(interaction.client, title="Command Error", color="error")

        if isinstance(error, app_commands.CommandOnCooldown):
            embed.description = f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds."
        elif isinstance(error, app_commands.MissingPermissions):
            embed.description = "You don't have the required permissions to run this command."
        elif isinstance(error, app_commands.CheckFailure):
            embed.description = "You are not allowed to use this command."
        else:
            embed.description = "An unexpected error occurred. The developers have been notified."
            logger.error(f"Unhandled error in slash command '{command_name}': {error}", exc_info=True)

        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error in on_app_command_error handler: {e}", exc_info=True)


# =============================================================================
# Cog Loading and Management
# =============================================================================

async def load_cogs() -> None:
    """Load all cog extensions."""
    cogs_to_load = [
        'minimal', 'api', 'events', 'fun',
        'games', 'info', 'meme', 'moderation',
        'ai', 'config', 'verification'
    ]

    for cog_name in cogs_to_load:
        try:
            module_path = f'cogs.{cog_name}'
            await bot.load_extension(module_path)
            bot.loaded_cogs[cog_name] = True
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f'Failed to load extension {cog_name}: {error_msg}')
            bot.failed_cogs[cog_name] = error_msg


async def main():
    """Main entry point for the bot."""
    # These setup steps are run once.
    setup_database()
    keep_alive(bot)  # MODIFICATION: Pass the bot instance to the web server
    logger.info("Web server started")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"discord.py: {discord.__version__}")
    logger.info(f"Platform: {platform.platform()}")

    # Resilient startup loop
    while True:
        try:
            logger.info("Attempting to start bot...")
            # The setup_hook will run load_cogs() for us on each connection.
            await bot.start(bot_token)
        except (discord.ConnectionClosed, discord.errors.GatewayNotFound, discord.errors.LoginFailure) as e:
            logger.error(f"A critical connection error occurred: {e}. Retrying in 15 seconds...")
            await SessionManager.close()  # Ensure the session is closed before retrying
            time.sleep(15)
        except Exception as e:
            logger.critical(f"An unrecoverable error occurred in main: {e}", exc_info=True)
            break  # Exit the loop on other critical errors


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually with keyboard interrupt")
    except Exception as e:
        logger.critical(f"Unhandled exception at top level: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # This will run when the loop in main() is broken
        asyncio.run(SessionManager.close())
        logger.info("Bot process is shutting down.")
