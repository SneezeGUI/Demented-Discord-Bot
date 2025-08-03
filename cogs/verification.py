# C:/Development/Projects/Demented-Discord-Bot/cogs/verification.py
import asyncio
import os
import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from urllib.parse import urlencode
import requests
from typing import Set, List

from quart import Quart, request, redirect

from data.utils import create_embed
from data.database_manager import (
    get_server_config_value, get_oauth_tokens, store_oauth_tokens, get_all_authorized_user_ids, delete_oauth_tokens
)
from cogs.ai import AICog

logger = logging.getLogger('demented_bot.verification')
DISCORD_API_URL = "https://discord.com/api/v10"


class VerificationCog(commands.Cog, name="Verification"):
    """Commands for member verification and management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.deauthorized_users: Set[int] = set()

        # --- Quart Web Server for Instant Callback ---
        self.app = Quart(__name__)
        self.setup_routes()
        self.bot.loop.create_task(self.app.run_task('0.0.0.0', 5000))

        # --- Background Tasks ---
        self.revert_deauthorized_users_task.start()
        # The pull-all task is started on demand, not here.
        self.active_pull_all_guilds: Set[int] = set()


    def cog_unload(self):
        self.revert_deauthorized_users_task.cancel()
        self.pull_all_members_task.cancel() # Ensure it's cancelled if running

    # --- Web Server and OAuth2 Callback ---
    def setup_routes(self):
        @self.app.route("/callback")
        async def callback():
            """Handles the OAuth2 redirect from Discord."""
            try:
                code = request.args.get('code')
                state = request.args.get('state') # This is the guild_id
                if not code or not state:
                    return "Error: Missing code or state from Discord redirect.", 400

                guild_id = int(state)
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    logger.error(f"OAuth2 callback received for an unknown guild ID: {guild_id}")
                    return "Error: The server this verification link came from could not be found.", 404

                user_id, access_token, refresh_token, expires_in = await self.exchange_code(code)
                if not user_id:
                    return "Error: Could not authenticate with Discord.", 500

                store_oauth_tokens(user_id, access_token, refresh_token, expires_in)
                logger.info(f"Successfully saved OAuth2 tokens for user {user_id}.")

                member = guild.get_member(user_id)
                if not member:
                    try:
                        member = await guild.fetch_member(user_id)
                    except discord.NotFound:
                        logger.warning(f"User {user_id} completed OAuth2 but was not found in guild {guild.name}. They may have left.")
                        return f"<html><body><h1>✅ Verification Successful!</h1><p>Your authorization has been recorded. You can now close this tab and return to Discord.</p></body></html>"

                if member:
                    await self._manage_roles(member)
                    logger.info(f"Instantly managed roles for {member.name} ({user_id}) in {guild.name} after verification.")

                return f"<html><body><h1>✅ Verification Successful!</h1><p>You have been verified in **{guild.name}**. You can now close this tab and return to Discord.</p></body></html>"

            except Exception as e:
                logger.error(f"An error occurred in the OAuth2 callback: {e}", exc_info=True)
                return "An unexpected error occurred during verification. Please try again.", 500

    async def exchange_code(self, code: str):
        """Exchanges an OAuth2 code for user tokens."""
        data = {
            'client_id': os.getenv('CLIENT_ID'),
            'client_secret': os.getenv('CLIENT_SECRET'),
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': os.getenv('REDIRECT_URI')
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post(f'{DISCORD_API_URL}/oauth2/token', data=data, headers=headers)
        if not r.ok:
            logger.error(f"Failed to exchange code for token. Status: {r.status_code}, Response: {r.text}")
            return None, None, None, None

        token_data = r.json()
        access_token = token_data['access_token']
        headers = {'Authorization': f'Bearer {access_token}'}
        user_req = requests.get(f'{DISCORD_API_URL}/users/@me', headers=headers)
        user_data = user_req.json()
        user_id = int(user_data['id'])

        return user_id, access_token, token_data['refresh_token'], token_data['expires_in']

    # --- Deauthorization Handling ---
    def schedule_role_revert(self, user_id: int):
        logger.info(f"Scheduling user {user_id} for role reversion due to deauthorization.")
        self.deauthorized_users.add(user_id)

    @tasks.loop(seconds=30.0)
    async def revert_deauthorized_users_task(self):
        if not self.deauthorized_users:
            return
        users_to_process = self.deauthorized_users.copy()
        self.deauthorized_users.clear()
        logger.info(f"Deauthorization task running for {len(users_to_process)} user(s).")
        for user_id in users_to_process:
            for guild in self.bot.guilds:
                try:
                    member = await guild.fetch_member(user_id)
                    if member:
                        await self._revert_roles(member)
                        await asyncio.sleep(1)
                except discord.NotFound:
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error fetching member {user_id} in guild {guild.name}: {e}")
                    continue

    @revert_deauthorized_users_task.before_loop
    async def before_revert_loop(self):
        await self.bot.wait_until_ready()

    async def _revert_roles(self, member: discord.Member):
        guild_id = member.guild.id
        verified_role_id = get_server_config_value(guild_id, "verified_role_id")
        unverified_role_id = get_server_config_value(guild_id, "unverified_role_id")
        try:
            roles_to_add, roles_to_remove = [], []
            if verified_role_id:
                verified_role = member.guild.get_role(verified_role_id)
                if verified_role and verified_role in member.roles:
                    roles_to_remove.append(verified_role)
            if unverified_role_id:
                unverified_role = member.guild.get_role(unverified_role_id)
                if unverified_role and unverified_role not in member.roles:
                    roles_to_add.append(unverified_role)
            if roles_to_add: await member.add_roles(*roles_to_add, reason="User deauthorized application.")
            if roles_to_remove: await member.remove_roles(*roles_to_remove, reason="User deauthorized application.")
            logger.info(f"Successfully reverted roles for {member.name}.")
        except Exception as e:
            logger.error(f"Failed to revert roles for {member.name}: {e}", exc_info=True)

    # --- Verification Commands ---
    verify_group = app_commands.Group(name="verify", description="Commands for the member verification system.")

    @verify_group.command(name="setup", description="Posts the verification panel in the current channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_verify(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        verified_role_id = get_server_config_value(guild_id, "verified_role_id")
        unverified_role_id = get_server_config_value(guild_id, "unverified_role_id")

        if not verified_role_id or not unverified_role_id:
            embed = create_embed(self.bot, title="Setup Error", color="error",
                                 description="Verification roles are not configured. Use `/config verification set-role` first.")
            await interaction.followup.send(embed=embed)
            return

        params = {
            'client_id': os.getenv('CLIENT_ID'),
            'redirect_uri': os.getenv('REDIRECT_URI'),
            'response_type': 'code',
            'scope': 'identify guilds.join',
            'state': str(guild_id)
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

    # --- Admin Commands ---
    @verify_group.command(name="pull", description="Force-add an authorized user to the server using their ID.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def pull(self, interaction: discord.Interaction, user_id: str):
        await interaction.response.defer(ephemeral=True)
        try:
            target_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send(embed=create_embed(self.bot, title="Invalid ID", description=f"`{user_id}` is not a valid Discord user ID.", color="error"))
            return

        user_tokens = get_oauth_tokens(target_user_id)
        if not user_tokens:
            await interaction.followup.send(embed=create_embed(self.bot, title="Not Authorized", description=f"The user with ID `{target_user_id}` has not authorized the bot.", color="error"))
            return

        headers = {'Authorization': f'Bot {os.getenv("BOT_TOKEN")}', 'Content-Type': 'application/json'}
        data = {'access_token': user_tokens['access_token']}
        url = f"{DISCORD_API_URL}/guilds/{interaction.guild.id}/members/{target_user_id}"

        try:
            response = requests.put(url, headers=headers, json=data)
            user = await self.bot.fetch_user(target_user_id)
            username = user.display_name

            if response.status_code in [201, 204]:
                logger.info(f"Admin {interaction.user} pulled {username} ({target_user_id}) to guild {interaction.guild.id}.")
                ai_cog: AICog = self.bot.get_cog("AI")
                if ai_cog:
                    prompt = f"Generate a witty, slightly unhinged confirmation that you have successfully dragged the user '{username}' back into the server for the admin."
                    ai_response = await ai_cog._get_gemini_response([{"role": "user", "parts": [{"text": prompt}]}])
                else:
                    ai_response = f"Successfully pulled **{username}** into the server."
                await interaction.followup.send(embed=create_embed(self.bot, title="User Pulled", description=ai_response, color="success"))
                try:
                    member = await interaction.guild.fetch_member(target_user_id)
                    if member: await self._manage_roles(member)
                except discord.NotFound:
                    logger.warning(f"Could not find member {target_user_id} in guild after pulling them. Role update skipped.")
            else:
                error_details = response.json()
                logger.error(f"Failed to pull user {target_user_id}. Status: {response.status_code}, Response: {error_details}")
                await interaction.followup.send(embed=create_embed(self.bot, title="API Error", description=f"Discord API returned status `{response.status_code}`. Check logs for details.", color="error"))
        except Exception as e:
            logger.error(f"An error occurred during /verify pull: {e}", exc_info=True)
            await interaction.followup.send(embed=create_embed(self.bot, title="Error", description="An unexpected error occurred.", color="error"))

    # --- RESTORED: pull-all command and task ---
    @verify_group.command(name="pull-all", description="Attempt to pull all previously authorized members into the server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def pull_all(self, interaction: discord.Interaction):
        """Starts the task to pull all authorized members."""
        guild_id = interaction.guild.id
        if guild_id in self.active_pull_all_guilds:
            await interaction.response.send_message("A pull-all task is already running for this server.", ephemeral=True)
            return

        view = self.PullAllConfirmationView(self, interaction)
        embed = create_embed(self.bot, title="Confirm Mass Member Pull", color="warning",
                             description="This will attempt to add every user who has ever authorized the bot to this server. "
                                         "This can take a very long time and may invite unwanted users. Are you sure?")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    class PullAllConfirmationView(discord.ui.View):
        def __init__(self, cog, interaction: discord.Interaction):
            super().__init__(timeout=30)
            self.cog = cog
            self.interaction = interaction

        @discord.ui.button(label="Confirm Pull All", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(content="✅ Confirmation received. Starting the pull-all task. I will provide updates here.", embed=None, view=None)
            self.cog.pull_all_members_task.start(self.interaction)
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(content="❌ Operation cancelled.", embed=None, view=None)
            self.stop()

    @tasks.loop(count=1)
    async def pull_all_members_task(self, interaction: discord.Interaction):
        """The background task that performs the pull-all operation."""
        guild = interaction.guild
        self.active_pull_all_guilds.add(guild.id)
        try:
            original_message = await interaction.original_response()
            authorized_user_ids = get_all_authorized_user_ids()
            if not authorized_user_ids:
                await interaction.edit_original_response(content="There are no authorized users in the database to pull.")
                return

            current_member_ids = {member.id for member in guild.members}
            users_to_pull = [uid for uid in authorized_user_ids if uid not in current_member_ids]
            total_to_pull = len(users_to_pull)
            logger.info(f"Starting pull-all task for guild {guild.name}. Found {total_to_pull} users to pull.")

            await interaction.edit_original_response(content=f"Found {total_to_pull} authorized members not in this server. Beginning the process...")

            success_count = 0
            fail_count = 0
            for i, user_id in enumerate(users_to_pull):
                user_tokens = get_oauth_tokens(user_id)
                if not user_tokens:
                    continue

                headers = {'Authorization': f'Bot {os.getenv("BOT_TOKEN")}', 'Content-Type': 'application/json'}
                data = {'access_token': user_tokens['access_token']}
                url = f"{DISCORD_API_URL}/guilds/{guild.id}/members/{user_id}"
                
                try:
                    response = requests.put(url, headers=headers, json=data)
                    if response.status_code in [201, 204]:
                        success_count += 1
                        logger.info(f"Pull-all: Successfully added user {user_id} to {guild.name}.")
                    else:
                        fail_count += 1
                        logger.warning(f"Pull-all: Failed to add user {user_id}. Status: {response.status_code}, Response: {response.text}")
                except Exception as e:
                    fail_count += 1
                    logger.error(f"Pull-all: Exception while adding user {user_id}: {e}")

                if (i + 1) % 10 == 0: # Update every 10 users
                    await interaction.edit_original_response(content=f"**Progress:** {i+1}/{total_to_pull}\n**Success:** {success_count} | **Failed:** {fail_count}")
                
                await asyncio.sleep(1.5) # Sleep to avoid rate limits

            final_message = f"**Pull-all task complete.**\n- Successfully added: {success_count}\n- Failed to add: {fail_count}"
            await interaction.edit_original_response(content=final_message)
            logger.info(f"Finished pull-all task for guild {guild.name}. Success: {success_count}, Failed: {fail_count}.")

        except Exception as e:
            logger.error(f"An error occurred in the pull_all_members_task for guild {guild.id}: {e}", exc_info=True)
            try:
                await interaction.edit_original_response(content="A critical error occurred during the task. Check logs for details.")
            except discord.NotFound:
                pass # The original message might have been deleted
        finally:
            self.active_pull_all_guilds.remove(guild.id)


    # --- Role Management and Event Listeners ---
    async def _manage_roles(self, member: discord.Member):
        guild_id = member.guild.id
        verified_role_id = get_server_config_value(guild_id, "verified_role_id")
        unverified_role_id = get_server_config_value(guild_id, "unverified_role_id")
        if not verified_role_id:
            logger.warning(f"Cannot manage roles: No 'verified_role_id' configured for guild {guild_id}.")
            return
        try:
            roles_to_add, roles_to_remove = [], []
            verified_role = member.guild.get_role(verified_role_id)
            if verified_role and verified_role not in member.roles:
                roles_to_add.append(verified_role)
            if unverified_role_id:
                unverified_role = member.guild.get_role(unverified_role_id)
                if unverified_role and unverified_role in member.roles:
                    roles_to_remove.append(unverified_role)
            if roles_to_add: await member.add_roles(*roles_to_add, reason="User completed verification.")
            if roles_to_remove: await member.remove_roles(*roles_to_remove, reason="User completed verification.")
        except discord.Forbidden:
            logger.error(f"PERMISSION ERROR: Missing 'Manage Roles' permission in guild {member.guild.name}.")
        except Exception as e:
            logger.error(f"Failed to manage roles for {member.name}: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
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
        except discord.Forbidden:
            logger.error(f"Missing permissions to assign unverified role in guild {member.guild.name}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))
