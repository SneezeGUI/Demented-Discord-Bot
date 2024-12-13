import discord
from discord.ext import commands
import asyncio

class SlashCog(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

#CLEAR
    @bot.slash_command(
      name='clear',
      description="Clears Messages",
    )
    async def clear(ctx, amount):
      await ctx.channel.purge(limit=int(amount))
      await ctx.respond("Cleared Messages")

      # CALL GAY
    @bot.slash_command(
      name='call-gay',
      description='calls user gay'
    )
    async def call_gay( ctx, member: discord.Member):
      await ctx.respond("About to lay the truth down...")
      await asyncio.sleep(1)
      await ctx.send(f"<@{member.id}> is Gay! lol")

      # ADD
    @bot.slash_command(
      name='add',
      description='adds two numbers'
    )
    async def add(ctx, left: int, right: int):
      """Adds two numbers together."""
      await ctx.respond(f"total is {left + right}")

    # SPAM
    @bot.slash_command(
      name="spam",
      description="Repeats a message multiple times.",
    )
    async def repeat(ctx, times: int, content='repeating...'):
      """Repeats a message multiple times."""
      await ctx.respond("Spamming...")
      for i in range(times):
        await ctx.send(content)

    #KICK
    @bot.slash_command(
      name = 'kick',
      description="Kicks a member off the server",
      # brief="Kick a member",
    )
    @commands.has_permissions(kick_members=True)
    async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
      try:
        await member.send("You have been kicked for the reasons of " + reason)
      except:
        await ctx.respond("The member has their DM's off")
      await member.kick(reason=reason)
      await ctx.respond(f"{member.mention} was kicked - Reason: " + reason)
#BAN
    @bot.slash_command(
      name = 'ban',
      help = "Bans a member from the server",
      # brief = "Ban a member")
    )
    @commands.has_permissions(ban_members=True)
    async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
      # try:
      #   await member.send("You have been banned for the reasons of " + reason)
      # except:
      #   await member.send("The member has their DM's off")
      await member.ban(reason=reason)
      await ctx.respond(f"{member.mention} was Banned! ")

#UNBAN
    @bot.slash_command(
      name = 'unban',
      aliases = 'unban',
      description = "Unbans a member from the server",
      # brief = "Unban a member")
    )
    @commands.has_permissions(ban_members=True)
    async def unban(ctx,member):
      banned_users = ctx.guild.bans()
      member_name = member

      async for banned_entry in banned_users:
        user = banned_entry.user

        if user.name  == member_name:
           await ctx.guild.unban(user)
           await ctx.send(f"{member_name} has been unbanned!")
        return
      await ctx.send(member = "was not found.")


### todo : fix commands below and add more

#MUTE
    @bot.slash_command(
      name = 'mute',
      description = "Mutes the member lol",
      # brief="Mute a member")
    )
    @commands.has_permissions(kick_members=True)
    async def mute(ctx, member: discord.Member):
      muted_role = ctx.guild.get_role(1315394620259176510)

      await member.add_roles(muted_role)
      await ctx.respond(member.mention + "has been muted")
#UNMUTE
    @bot.slash_command(
      aliases = 'unmute',
      description = "Unmute the member.",
      # brief = "Unmute a member")
    )
    @commands.has_permissions(kick_members=True)
    async def unmute(ctx, member: discord.Member):
      unmuted_role = ctx.guild.get_role(1315394620259176510)

      await member.remove_roles(unmuted_role)
      await ctx.respond(member.mention + "has been unmuted")

def setup(bot):
  bot.add_cog(SlashCog(bot))