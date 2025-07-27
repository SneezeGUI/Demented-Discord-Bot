# C:/Development/Projects/Demented-Discord-Bot/cogs/config.py

import discord
import json
import logging
from discord import app_commands
from discord.ext import commands
from typing import Literal  # MODIFICATION: Import Literal from typing

from data.database_manager import get_server_config_value, set_server_config_value

logger = logging.getLogger('demented_bot.config')


class ConfigCog(commands.Cog, name="Configuration"):
    """Commands for server-specific bot configuration."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Command Groups ---
    config_group = app_commands.Group(name="config", description="Configure the bot for this server.")
    autonomy_group = app_commands.Group(name="autonomy", parent=config_group,
                                        description="Configure autonomous behavior.")
    verification_group = app_commands.Group(name="verification", parent=config_group,
                                            description="Configure the member verification system.")
    restrictions_group = app_commands.Group(name="restrictions", parent=config_group,
                                            description="Manage channel restrictions.")

    @config_group.command(name="view", description="View the current configuration for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_config(self, interaction: discord.Interaction):
        """Displays the current server-specific settings."""
        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id

        # Fetch all config values
        raw_autonomy_channels = get_server_config_value(guild_id, "autonomy_channels")
        autonomy_channel_ids = json.loads(raw_autonomy_channels) if raw_autonomy_channels else []

        raw_restricted_channels = get_server_config_value(guild_id, "restricted_channels")
        restricted_channel_ids = json.loads(raw_restricted_channels) if raw_restricted_channels else []

        verified_role_id = get_server_config_value(guild_id, "verified_role_id")
        unverified_role_id = get_server_config_value(guild_id, "unverified_role_id")

        embed = discord.Embed(title=f"⚙️ Configuration for {interaction.guild.name}", color=discord.Color.blue())

        # Format Autonomy Channels
        if not autonomy_channel_ids:
            autonomy_value = "No channels configured. The bot will not start conversations on its own."
        else:
            autonomy_value = "\n".join(f"<#{cid}>" for cid in autonomy_channel_ids)
        embed.add_field(name="Autonomous Chat Channels", value=autonomy_value, inline=False)

        # Format Restricted Channels
        if not restricted_channel_ids:
            restricted_value = "No channels restricted. The bot can speak anywhere it's invited."
        else:
            restricted_value = "\n".join(f"<#{cid}>" for cid in restricted_channel_ids)
        embed.add_field(name="🚫 Restricted Channels (Blacklist)", value=restricted_value, inline=False)

        # Format Verification Roles
        verified_value = f"<@&{verified_role_id}>" if verified_role_id else "Not set."
        unverified_value = f"<@&{unverified_role_id}>" if unverified_role_id else "Not set."

        embed.add_field(name="✅ Verified Role", value=verified_value, inline=True)
        embed.add_field(name="⏳ Unverified Role", value=unverified_value, inline=True)

        embed.set_footer(
            text="Use /config autonomy, /config restrictions, and /config verification to manage settings.")
        await interaction.followup.send(embed=embed)

    # --- Autonomy Commands ---
    @autonomy_group.command(name="add-channel", description="Allow the bot to start conversations in a channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to add.")
    async def add_autonomy_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Adds a channel to the autonomy list."""
        guild_id = interaction.guild.id
        raw_channels = get_server_config_value(guild_id, "autonomy_channels")
        channel_ids = json.loads(raw_channels) if raw_channels else []

        if channel.id in channel_ids:
            await interaction.response.send_message(f"✅ <#{channel.id}> is already in the autonomy list.",
                                                    ephemeral=True)
            return

        channel_ids.append(channel.id)
        set_server_config_value(guild_id, "autonomy_channels", json.dumps(channel_ids))
        await interaction.response.send_message(f"👍 Okay, I will now sometimes start conversations in <#{channel.id}>.",
                                                ephemeral=True)

    @autonomy_group.command(name="remove-channel", description="Stop the bot from starting conversations in a channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to remove.")
    async def remove_autonomy_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Removes a channel from the autonomy list."""
        guild_id = interaction.guild.id
        raw_channels = get_server_config_value(guild_id, "autonomy_channels")
        channel_ids = json.loads(raw_channels) if raw_channels else []

        if channel.id not in channel_ids:
            await interaction.response.send_message(f"🤔 <#{channel.id}> isn't in the autonomy list.", ephemeral=True)
            return

        channel_ids.remove(channel.id)
        set_server_config_value(guild_id, "autonomy_channels", json.dumps(channel_ids))
        await interaction.response.send_message(
            f"👎 Understood. I will no longer start conversations in <#{channel.id}>.", ephemeral=True)

    # --- NEW: Verification Config Commands ---
    @verification_group.command(name="set-role", description="Set the roles for the verification system.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(role_type="The type of role to set.", role="The role to assign.")
    async def set_verification_role(self, interaction: discord.Interaction,
                                    role_type: Literal["verified", "unverified"],  # MODIFICATION: Use Literal directly
                                    role: discord.Role):
        """Sets the verified or unverified role for the server."""
        guild_id = interaction.guild.id
        db_key = f"{role_type}_role_id"
        set_server_config_value(guild_id, db_key, role.id)
        await interaction.response.send_message(
            f"✅ The **{role_type}** role has been set to {role.mention}.", ephemeral=True
        )

    # --- Restriction Commands ---
    @restrictions_group.command(name="add-channel", description="Prevent the bot from speaking in a specific channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to restrict.")
    async def add_restricted_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Adds a channel to the restriction blacklist."""
        guild_id = interaction.guild.id
        raw_channels = get_server_config_value(guild_id, "restricted_channels")
        channel_ids = json.loads(raw_channels) if raw_channels else []

        if channel.id in channel_ids:
            await interaction.response.send_message(f"✅ <#{channel.id}> is already restricted.", ephemeral=True)
            return

        channel_ids.append(channel.id)
        set_server_config_value(guild_id, "restricted_channels", json.dumps(channel_ids))
        await interaction.response.send_message(f"🚫 Okay, I will no longer speak in <#{channel.id}>.", ephemeral=True)

    @restrictions_group.command(name="remove-channel", description="Allow the bot to speak in a channel again.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to un-restrict.")
    async def remove_restricted_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Removes a channel from the restriction blacklist."""
        guild_id = interaction.guild.id
        raw_channels = get_server_config_value(guild_id, "restricted_channels")
        channel_ids = json.loads(raw_channels) if raw_channels else []

        if channel.id not in channel_ids:
            await interaction.response.send_message(f"🤔 <#{channel.id}> isn't on the restriction list.", ephemeral=True)
            return

        channel_ids.remove(channel.id)
        set_server_config_value(guild_id, "restricted_channels", json.dumps(channel_ids))
        await interaction.response.send_message(f"🗣️ Understood. I am now allowed to speak in <#{channel.id}> again.",
                                                ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCog(bot))