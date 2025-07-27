# C:/Development/Projects/Demented-Discord-Bot/cogs/minimal.py

import discord
from discord import app_commands
from discord.ext import commands
from data.helper_functions import timed_command
import asyncio

class MinimalCog(commands.Cog):
    """A minimal cog with basic commands for testing."""

    def __init__(self, bot):
        self.bot = bot

    # REMOVED: The duplicate 'hello' prefix command to resolve the conflict with cogs/fun.py
    # The 'hello-slash' command remains as a good example.

    @app_commands.command(name="hello-slash", description="A simple hello slash command")
    @timed_command("Hello command execution")
    async def hello_slash(self, interaction: discord.Interaction):
        """A simple hello slash command."""
        await interaction.response.send_message(f"Hello, {interaction.user.mention}!")

    @app_commands.command(name="choose", description="Choose between options")
    @app_commands.choices(option=[
        app_commands.Choice(name="Option 1", value="1"),
        app_commands.Choice(name="Option 2", value="2"),
        app_commands.Choice(name="Option 3", value="3"),
    ])
    async def choose(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        """Choose between options."""
        await interaction.response.send_message(f"You chose {option.name} (value: {option.value})")

    @app_commands.command(name="defer-example", description="Example of deferred response")
    async def defer_example(self, interaction: discord.Interaction):
        """Example of deferred response for long operations."""
        await interaction.response.defer(thinking=True)
        await asyncio.sleep(4)
        await interaction.followup.send("This response was deferred while I was thinking!")

async def setup(bot):
    await bot.add_cog(MinimalCog(bot))