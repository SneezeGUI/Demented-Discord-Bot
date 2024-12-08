import discord
from discord.ext import commands
import asyncio


class SlashCog(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

    @bot.slash_command(
      name='first-slash',
      description='default command to get active dev',

    )
    async def first_slash(ctx):
      await ctx.respond("You executed a slash command!")

    @bot.slash_command(
      name='clear',
      description="Clears Messages",
    )
    async def clear(ctx, amount):
      await ctx.channel.purge(limit=int(amount))
      await ctx.respond("Cleared Messages")

    @bot.slash_command(
      name='call-gay',
      description='calls user gay'
    )
    async def call_gay(ctx, member: discord.Member):
      await ctx.respond("About to lay the truth down...")
      await asyncio.sleep(1)
      await ctx.send(f"<@{member.id}> is Gay! lol")

    @bot.slash_command(
      name='add',
      description='adds two numbers'
    )
    async def add(ctx, left: int, right: int):
      """Adds two numbers together."""
      await ctx.respond(f"total is {left + right}")

    @bot.slash_command(
      name="spam",
      description="Repeats a message multiple times.",
    )
    async def repeat(ctx, times: int, content='repeating...'):
      """Repeats a message multiple times."""
      await ctx.respond("Spamming...")
      for i in range(times):
        await ctx.send(content)

def setup(bot):
  bot.add_cog(SlashCog(bot))