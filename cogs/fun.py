# C:/Development/Projects/Demented-Discord-Bot/cogs/fun.py

from random import choice, randint, shuffle
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hello", description="A friendly greeting!")
    async def hello(self, interaction: discord.Interaction):
        """A simple hello command."""
        await interaction.response.send_message(f"{choice(('Hello', 'Hi', 'Hey', 'Hiya', 'Yo'))} {interaction.user.mention}!")

    @app_commands.command(name="slap", description="Slap a user, with an optional reason.")
    async def slap(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "for no reason"):
        """Slaps a member."""
        await interaction.response.send_message(f"{interaction.user.display_name} slapped {member.mention} {reason}!")

    @app_commands.command(name="echo", description="Repeats a message.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.guild_id)
    async def echo(self, interaction: discord.Interaction, message: str):
        """Repeats a user's message."""
        await interaction.response.send_message(message)

    @app_commands.command(name="call-gay", description="Calls a user gay... for fun, of course.")
    async def call_gay(self, interaction: discord.Interaction, member: discord.Member):
        """A playful command to call someone gay."""
        await interaction.response.send_message(f"{member.mention} is Gay! lol 🏳️‍🌈")

    @app_commands.command(name="8ball", description="Ask the magical 8-ball a question.")
    async def _8ball(self, interaction: discord.Interaction, question: str):
        responses = ["Yes.", "No.", "Maybe.", "Definitely!", "Ask again later.", "Not sure.", "Absolutely not."]
        await interaction.response.send_message(f"🎱 **Question:** {question}\n🎱 **Answer:** {choice(responses)}")

    @app_commands.command(name="shuffle", description="Shuffles the provided list of words.")
    async def shuffle_words(self, interaction: discord.Interaction, words: str):
        word_list = words.split()
        shuffle(word_list)
        shuffled_text = " ".join(word_list)
        await interaction.response.send_message(f"Shuffled: {shuffled_text}")

    @app_commands.command(name="roll", description="Roll a random number (default 1-100).")
    async def roll(self, interaction: discord.Interaction, maximum: app_commands.Range[int, 1, 1000000] = 100):
        result = randint(1, maximum)
        await interaction.response.send_message(f"🎲 You rolled a **{result}** (1-{maximum})!")

    @app_commands.command(name="hug", description="Give a hug to another user.")
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} gives a warm hug to {member.mention}! 🤗")

    @app_commands.command(name="reverse", description="Reverses the given text.")
    async def reverse_text(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message(f"Reversed: {text[::-1]}")

    @app_commands.command(name="tableflip", description="Flips a table in style!")
    async def tableflip(self, interaction: discord.Interaction):
        await interaction.response.send_message("(╯°□°）╯︵ ┻━┻")

    @app_commands.command(name="pat", description="Gently pat another user.")
    async def pat(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} gently pats {member.mention} on the head. 😊")


async def setup(bot):
    await bot.add_cog(Fun(bot))