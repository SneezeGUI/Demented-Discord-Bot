# C:/Development/Projects/Demented-Discord-Bot/cogs/api.py

import logging
import discord
from discord import app_commands, Embed
from discord.ext import commands
from data.helper_functions import get_joke, get_bored_activity, timed_command

logger = logging.getLogger('demented_bot.api')


class ApiCog(commands.Cog, name="API Commands"):
    """Commands that interact with external APIs"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Helper Methods for Embeds ---

    def _create_joke_embed(self, category: str, joke_text: str, is_twopart: bool, setup: str, delivery: str) -> Embed:
        """Creates a consistent embed for jokes."""
        embed = Embed(title=f"{category.capitalize()} Joke", color=discord.Color.random())
        if is_twopart:
            embed.add_field(name="Setup", value=setup, inline=False)
            embed.add_field(name="Punchline", value=f"||{delivery}||", inline=False)
        else:
            embed.description = joke_text
        return embed

    def _create_bored_embed(self, data: dict, participants: int) -> Embed:
        """Creates a consistent embed for the 'bored' command."""
        activity = data.get('activity', "No activity found")
        activity_type = data.get('type', "unknown")
        price = data.get('price', 0)
        accessibility = data.get('accessibility', 0)

        embed = Embed(title="Bored? Here's an idea!", color=discord.Color.green())
        embed.add_field(name="Activity", value=activity, inline=False)
        embed.add_field(name="Type", value=activity_type.capitalize(), inline=True)

        price_str = "Free" if price == 0 else "Low" if price < 0.3 else "Medium" if price < 0.7 else "High"
        access_str = "Very accessible" if accessibility < 0.3 else "Moderately accessible" if accessibility < 0.7 else "Less accessible"

        embed.add_field(name="Cost", value=price_str, inline=True)
        embed.add_field(name="Accessibility", value=access_str, inline=True)
        embed.set_footer(text=f"For {participants} participant(s)")
        return embed

    # --- Joke Commands ---

    @commands.command(
        aliases=['j'],
        help="Tells a joke from various categories (programming, spooky, christmas, dark, misc)",
        brief="Tells a dark joke by default"
    )
    @commands.cooldown(3, 30, commands.BucketType.user)
    async def joke(self, ctx: commands.Context, category="Dark"):
        """Get a joke from the JokeAPI."""
        async with ctx.typing():
            joke_text, is_twopart, setup, delivery = await get_joke(self.bot, category)
            embed = self._create_joke_embed(category, joke_text, is_twopart, setup, delivery)
            await ctx.send(embed=embed)

    @app_commands.command(
        name="joke-api",
        description="Get a joke from various categories"
    )
    @timed_command("Joke slash command execution")
    async def joke_slash(self, interaction: discord.Interaction, category: str = "Dark"):
        """Get a joke from the JokeAPI."""
        await interaction.response.defer()
        joke_text, is_twopart, setup, delivery = await get_joke(self.bot, category)
        embed = self._create_joke_embed(category, joke_text, is_twopart, setup, delivery)
        await interaction.followup.send(embed=embed)

    # --- Bored Commands ---

    @commands.command(
        aliases=['imbored'],
        help="Gives an activity idea for a specified number of participants",
        brief="Gives a purpose to bored souls"
    )
    @commands.cooldown(3, 15, commands.BucketType.user)
    async def bored(self, ctx: commands.Context, people: str = "1"):
        """Get a random activity suggestion for bored people."""
        async with ctx.typing():
            try:
                participants = int(people)
                if not (1 <= participants <= 10):
                    await ctx.send("Please specify a number of participants between 1 and 10.")
                    return
            except ValueError:
                await ctx.send("Please specify a valid number of participants.")
                return

            data = await get_bored_activity(participants)
            if not data:
                await ctx.send("Sorry, couldn't get an activity right now. Try again later.")
                return

            embed = self._create_bored_embed(data, participants)
            await ctx.send(embed=embed)

    @app_commands.command(
        name="bored",
        description="Get a random activity suggestion when you're bored"
    )
    @app_commands.describe(participants="The number of people (1-10).")
    @timed_command("Bored slash command execution")
    async def bored_slash(self, interaction: discord.Interaction, participants: app_commands.Range[int, 1, 10] = 1):
        """Get a random activity suggestion for bored people."""
        await interaction.response.defer()
        data = await get_bored_activity(participants)
        if not data:
            await interaction.followup.send("Sorry, couldn't get an activity right now. Try again later.")
            return

        embed = self._create_bored_embed(data, participants)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Sets up the cog."""
    await bot.add_cog(ApiCog(bot))