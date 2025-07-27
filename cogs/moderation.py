# C:/Development/Projects/Demented-Discord-Bot/cogs/moderation.py

import discord
from discord import app_commands
from discord.ext import commands
import datetime


class Moderation(commands.Cog):
    """Commands for server moderation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='clear', description="Clears a specified number of messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True, thinking=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Successfully cleared {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="kick", description="Kicks a member from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.send(f"You have been kicked from **{interaction.guild.name}** for: {reason}")
        except discord.Forbidden:
            pass
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 {member.mention} was kicked. Reason: {reason}")

    @app_commands.command(name="ban", description="Bans a member from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} was banned! Reason: {reason}")

    @app_commands.command(name="unban", description="Unbans a user from the server by their ID.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Manual unban."):
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message(f"Could not find a user with the ID `{user_id}`.", ephemeral=True)
            return
        try:
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(f"✅ {user.name} has been unbanned!")
        except discord.NotFound:
            await interaction.response.send_message(f"{user.name} was not found in the ban list.")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to unban members.")

    @app_commands.command(name="mute", description="Mutes a member for a specified duration (timeout).")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member,
                   duration: app_commands.Range[int, 1, 40320],
                   reason: str = "No reason provided"):

        expiration = discord.utils.utcnow() + datetime.timedelta(minutes=duration)
        await member.timeout(expiration, reason=reason)

        embed = discord.Embed(title="Member Muted",
                              description=f"{member.mention} has been muted for {duration} minutes.",
                              color=discord.Color.orange())
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Expires", value=f"<t:{int(expiration.timestamp())}:R>", inline=False)
        embed.set_footer(text=f"Muted by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unmute", description="Removes a timeout from a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Manual unmute."):
        await member.timeout(None, reason=reason)
        embed = discord.Embed(title="Member Unmuted", description=f"{member.mention} has been unmuted.",
                              color=discord.Color.green())
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Unmuted by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))