# C:/Development/Projects/Demented-Discord-Bot/cogs/verification.py
import asyncio
import os
import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from urllib.parse import urlencode
import requests
from typing import List, Set

from data.utils import create_embed
from data.database_manager import (
    get_server_config_value, get_oauth_tokens, get_all_authorized_user_ids
)
from cogs.ai import AICog

logger = logging.getLogger('demented_bot.verification')
DISCORD_API_URL = "https://discord.com/api/v10"


class VerificationCog(commands.Cog, name="Verification"):
    """Commands for member verification and management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.deauthorized_users: Set[int] = set()
        self.verify_new_members_task.start()
        self.revert_deauthorized_users_task.start()

    def cog_unload(self):
        self.verify_new_members_task.cancel()
        self.revert_deauthorized_users_task.cancel()

    # --- Deauthorization Handling ---
    def schedule_role_revert(self, user_id: int):
        """Schedules a user ID to have their roles reverted by the background task."""
        logger.info(f"Scheduling user {user_id} for role reversion due to deauthorization.")
        self.deauthorized_users.add(user_id)

    @tasks.loop(seconds=30.0)
    async def revert_deauthorized_users_task(self):
        """Periodically processes users who have deauthorized the bot."""
        if not self.deauthorized_users:
            return

        # Process a copy of the set to avoid issues if new users are added during processing
        users_to_process = self.deauthorized_users.copy()
        self.deauthorized_users.clear()
        logger.info(f"Deauthorization task running for {len(users_to_process)} user(s).")

        for user_id in users_to_process:
            for guild in self.bot.guilds:
                # --- MODIFICATION: Use fetch_member for reliability ---
                try:
                    # fetch_member makes a direct API call, bypassing the unreliable cache.
                    member = await guild.fetch_member(user_id)
                    if member:
                        await self._revert_roles(member)
                        # Add a small sleep to prevent hitting rate limits if many users deauth at once.
                        await asyncio.sleep(1)
                except discord.NotFound:
                    # This is expected if the user is no longer in this specific guild.
                    logger.debug(f"User {user_id} not found in guild {guild.name} during deauth check.")
                    continue
                except discord.Forbidden:
                    # This can happen if the bot loses permissions in a server.
                    logger.warning(f"Lacking 'View Members' permission in guild {guild.name} to check for deauthed user {user_id}.")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error fetching member {user_id} in guild {guild.name}: {e}")
                    continue
                # --- END MODIFICATION ---

    @revert_deauthorized_users_task.before_loop
    async def before_revert_loop(self):
        await self.bot.wait_until_ready()
        logger.info("Deauthorization task loop is ready and waiting.")

    async def _revert_roles(self, member: discord.Member):
        """Removes verified role and adds unverified role for a member."""
        guild_id = member.guild.id
        logger.debug(f"Reverting roles for deauthorized member {member.name} ({member.id}) in guild {guild_id}.")

        verified_role_id = get_server_config_value(guild_id, "verified_role_id")
        unverified_role_id = get_server_config_value(guild_id, "unverified_role_id")

        try:
            roles_to_add = []
            roles_to_remove = []

            if verified_role_id:
                verified_role = member.guild.get_role(verified_role_id)
                if verified_role and verified_role in member.roles:
                    roles_to_remove.append(verified_role)

            if unverified_role_id:
                unverified_role = member.guild.get_role(unverified_role_id)
                if unverified_role and unverified_role not in member.roles:
                    roles_to_add.append(unverified_role)

            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="User deauthorized application.")
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="User deauthorized application.")

            logger.info(f"Successfully reverted roles for {member.name}.")
        except discord.Forbidden:
            logger.error(f"PERMISSION ERROR: Cannot revert roles for {member.name} in guild {guild_id}.")
        except Exception as e:
            logger.error(f"Failed to revert roles for {member.name}: {e}", exc_info=True)

    # --- Verification Handling ---
    verify_group = app_commands.Group(name="verify", description="Commands for the member verification system.")

    @tasks.loop(seconds=15.0)
    async def verify_new_members_task(self):
        """Periodically checks for members with the unverified role who have since completed OAuth2 verification."""
        try:
            for guild in self.bot.guilds:
                unverified_role_id = get_server_config_value(guild.id, "unverified_role_id")
                if not unverified_role_id: continue

                unverified_role = guild.get_role(unverified_role_id)
                if not unverified_role: continue

                for member in unverified_role.members:
                    if get_oauth_tokens(member.id):
                        logger.info(f"Task found newly verified user: {member.name} ({member.id}). Applying roles.")
                        await self._manage_roles(member)
                        await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"An error occurred in the verify_new_members_task: {e}", exc_info=True)

    @verify_new_members_task.before_loop
    async def before_verify_loop(self):
        await self.bot.wait_until_ready()
        logger.info("Verification task loop is ready and waiting.")

    @verify_group.command(name="setup", description="Posts the verification panel in the current channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_verify(self, interaction: discord.Interaction):
        """Posts the verification embed and button."""
        await interaction.response.defer(ephemeral=True)

        verified_role_id = get_server_config_value(interaction.guild.id, "verified_role_id")
        unverified_role_id = get_server_config_value(interaction.guild.id, "unverified_role_id")

        if not verified_role_id or not unverified_role_id:
            embed = create_embed(
                self.bot, title="Setup Error", color="error",
                description="Verification roles are not configured for this server. "
                            "Please use `/config verification set-role` to set both the "
                            "`verified` and `unverified` roles first.")
            await interaction.followup.send(embed=embed)
            return

        params = {
            'client_id': os.getenv('CLIENT_ID'),
            'redirect_uri': os.getenv('REDIRECT_URI'),
            'response_type': 'code',
            'scope': 'identify guilds.join',
            'state': str(interaction.guild.id)
        }
        auth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"

        embed = create_embed(
            self.bot,
            title="🔒 Server Verification Required",
            description=(
                "Welcome! To ensure the safety and integrity of our community, we require all members to complete a quick verification.\n\n"
                "This process confirms you are a human and grants the bot permission to add you back to the server if you ever leave or are removed by mistake.\n\n"
                "▶️ **Click the button below to begin.**"
            ),
            footer="Your information is used solely for verification and server management."
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Verify Me", style=discord.ButtonStyle.success, url=auth_url))

        try:
            await interaction.channel.send(embed=embed, view=view)
            await interaction.followup.send("✅ Verification panel posted successfully.")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to send messages in this channel.")

    @verify_group.command(name="pull", description="Force-add an authorized user to the server using their ID.")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(user_id="The Discord ID of the user to pull.")
    async def pull(self, interaction: discord.Interaction, user_id: str):
        """Adds a user who has previously authorized the bot to the current server."""
        await interaction.response.defer(ephemeral=True)

        try:
            target_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send(embed=create_embed(self.bot, title="Invalid ID",
                                                               description=f"`{user_id}` is not a valid Discord user ID.",
                                                               color="error"))
            return

        user_tokens = get_oauth_tokens(target_user_id)
        if not user_tokens:
            await interaction.followup.send(embed=create_embed(self.bot, title="Not Authorized",
                                                               description=f"The user with ID `{target_user_id}` has not authorized the bot. They must complete the verification process first.",
                                                               color="error"))
            return

        headers = {
            'Authorization': f'Bot {os.getenv("BOT_TOKEN")}',
            'Content-Type': 'application/json'
        }
        data = {'access_token': user_tokens['access_token']}
        url = f"{DISCORD_API_URL}/guilds/{interaction.guild.id}/members/{target_user_id}"

        try:
            response = requests.put(url, headers=headers, json=data)
            user = await self.bot.fetch_user(target_user_id)
            username = user.display_name

            if response.status_code in [201, 204]:
                logger.info(
                    f"Admin {interaction.user} pulled {username} ({target_user_id}) to guild {interaction.guild.id}.")
                ai_cog: AICog = self.bot.get_cog("AI")
                if ai_cog:
                    prompt = f"Generate a witty, slightly unhinged confirmation that you have successfully dragged the user '{username}' back into the server for the admin."
                    ai_response = await ai_cog._get_gemini_response([{"role": "user", "parts": [{"text": prompt}]}])
                else:
                    ai_response = f"Successfully pulled **{username}** into the server."

                await interaction.followup.send(
                    embed=create_embed(self.bot, title="User Pulled", description=ai_response, color="success"))

                try:
                    member = await interaction.guild.fetch_member(target_user_id)
                    if member:
                        await self._manage_roles(member)
                except discord.NotFound:
                    logger.warning(
                        f"Could not find member {target_user_id} in guild after pulling them. Role update skipped.")
            else:
                error_details = response.json()
                logger.error(
                    f"Failed to pull user {target_user_id}. Status: {response.status_code}, Response: {error_details}")
                await interaction.followup.send(embed=create_embed(self.bot, title="API Error",
                                                                   description=f"Discord API returned status `{response.status_code}`. Check logs for details.",
                                                                   color="error"))
        except discord.NotFound:
            await interaction.followup.send(embed=create_embed(self.bot, title="User Not Found",
                                                               description=f"Could not find a user with the ID `{target_user_id}`.",
                                                               color="error"))
        except Exception as e:
            logger.error(f"An error occurred during /verify pull: {e}", exc_info=True)
            await interaction.followup.send(
                embed=create_embed(self.bot, title="Error", description="An unexpected error occurred.", color="error"))

    @verify_group.command(name="pull-all",
                          description="Attempts to pull all previously verified users into this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def pull_all(self, interaction: discord.Interaction):
        """Iterates through all users who have authorized the bot and attempts to add them to the current server."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        authorized_user_ids = get_all_authorized_user_ids()
        if not authorized_user_ids:
            await interaction.followup.send(
                embed=create_embed(self.bot, title="No Users", description="No authorized users found in the database.",
                                   color="warning"))
            return

        target_guild = interaction.guild
        total_users = len(authorized_user_ids)
        success_count, already_present_count, fail_count = 0, 0, 0

        logger.info(
            f"Admin {interaction.user} initiated a pull-all for {total_users} users to guild {target_guild.id}.")

        for user_id in authorized_user_ids:
            user_tokens = get_oauth_tokens(user_id)
            if not user_tokens:
                fail_count += 1
                logger.warning(f"Could not retrieve tokens for user {user_id} during pull-all, skipping.")
                continue

            url = f"{DISCORD_API_URL}/guilds/{target_guild.id}/members/{user_id}"
            headers = {'Authorization': f'Bot {os.getenv("BOT_TOKEN")}', 'Content-Type': 'application/json'}
            data = {'access_token': user_tokens['access_token']}

            try:
                response = requests.put(url, headers=headers, json=data)
                if response.status_code == 201:
                    success_count += 1
                    try:
                        member = await target_guild.fetch_member(user_id)
                        if member:
                            await self._manage_roles(member)
                    except discord.NotFound:
                        logger.warning(f"Could not find member {user_id} in guild after pull-all. Role update skipped.")
                elif response.status_code == 204:
                    already_present_count += 1
                else:
                    fail_count += 1
                    logger.error(
                        f"Failed to pull user {user_id} during pull-all. Status: {response.status_code}, Response: {response.text}")
            except requests.RequestException as e:
                fail_count += 1
                logger.error(f"HTTP error while trying to pull user {user_id} during pull-all: {e}")

        summary_embed = create_embed(
            self.bot,
            title="Pull All Users Report",
            description=f"Finished attempting to pull **{total_users}** authorized users to **{target_guild.name}**.",
            fields=[
                ("Successfully Added", f"✅ {success_count}", True),
                ("Already Present", f"ℹ️ {already_present_count}", True),
                ("Failed", f"❌ {fail_count}", True)
            ]
        )
        await interaction.followup.send(embed=summary_embed)

    async def _manage_roles(self, member: discord.Member):
        """Helper function to add/remove verification roles with detailed logging."""
        guild_id = member.guild.id
        logger.debug(f"Managing roles for {member.name} ({member.id}) in guild {guild_id}.")

        verified_role_id = get_server_config_value(guild_id, "verified_role_id")
        unverified_role_id = get_server_config_value(guild_id, "unverified_role_id")

        if not verified_role_id:
            logger.warning(f"Cannot manage roles: No 'verified_role_id' configured for guild {guild_id}.")
            return

        try:
            roles_to_add = []
            roles_to_remove = []

            verified_role = member.guild.get_role(verified_role_id)
            if verified_role:
                if verified_role not in member.roles:
                    roles_to_add.append(verified_role)
                    logger.debug(f"Queueing ADD of role '{verified_role.name}' for {member.name}.")
            else:
                logger.error(f"Configuration error: Could not find verified role with ID {verified_role_id} in guild {guild_id}.")

            if unverified_role_id:
                unverified_role = member.guild.get_role(unverified_role_id)
                if unverified_role:
                    if unverified_role in member.roles:
                        roles_to_remove.append(unverified_role)
                        logger.debug(f"Queueing REMOVE of role '{unverified_role.name}' for {member.name}.")
                else:
                    logger.warning(f"Configuration warning: Could not find unverified role with ID {unverified_role_id} in guild {guild_id}.")

            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="User completed verification.")
                logger.info(f"Successfully ADDED {len(roles_to_add)} role(s) to {member.name}.")

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="User completed verification.")
                logger.info(f"Successfully REMOVED {len(roles_to_remove)} role(s) from {member.name}.")

            if not roles_to_add and not roles_to_remove:
                logger.debug(f"No role changes needed for {member.name}.")

        except discord.Forbidden:
            logger.error(f"PERMISSION ERROR: Missing 'Manage Roles' permission or bot's role is too low in hierarchy to manage roles for {member.name} in guild {member.guild.name}.")
        except Exception as e:
            logger.error(f"Failed to manage roles for {member.name}: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Assigns the unverified role to new members, or re-verifies them."""
        if get_oauth_tokens(member.id):
            logger.info(f"Verified user {member.name} re-joined. Applying roles.")
            await self._manage_roles(member)
            return

        unverified_role_id = get_server_config_value(member.guild.id, "unverified_role_id")
        if not unverified_role_id:
            return

        try:
            unverified_role = member.guild.get_role(unverified_role_id)
            if unverified_role:
                await member.add_roles(unverified_role, reason="New member join.")
                logger.info(f"Assigned unverified role to {member.name}.")
        except discord.Forbidden:
            logger.error(f"Missing permissions to assign unverified role in guild {member.guild.name}.")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Listener that triggers when a member's roles change.
        Ensures that if the verified role is added, the unverified one is removed.
        """
        verified_role_id = get_server_config_value(after.guild.id, "verified_role_id")
        if not verified_role_id:
            return

        verified_role = after.guild.get_role(verified_role_id)
        if not verified_role:
            return

        if verified_role not in before.roles and verified_role in after.roles:
            logger.info(f"User {after.name} received the verified role. Running role cleanup.")
            await self._manage_roles(after)


async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))