# C:/Development/Projects/Demented-Discord-Bot/cogs/info.py

from datetime import datetime
from typing import Optional
import discord
from discord import app_commands, Embed, Member
from discord.ext import commands


class InfoCog(commands.Cog, name="Information"):
    def __init__(self, bot):
        self.bot = bot

    def _create_user_info_embed(self, target: Member) -> Embed:
        """Helper function to create the user info embed."""
        embed = Embed(title=f"Information for {target.display_name}",
                      colour=target.colour or discord.Color.blurple(),
                      timestamp=datetime.utcnow())

        embed.set_thumbnail(url=target.display_avatar.url)

        fields = [
            ("Full Name", str(target), True),
            ("ID", target.id, True),
            ("Is Bot?", "Yes" if target.bot else "No", True),
            ("Top Role", target.top_role.mention, True),
            ("Status", str(target.status).title(), True),
            ("Activity",
             f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''}",
             True),
            ("Created", f"<t:{int(target.created_at.timestamp())}:R>", True),
            ("Joined", f"<t:{int(target.joined_at.timestamp())}:R>", True),
            ("Boosting?", "Yes" if target.premium_since else "No", True)
        ]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        return embed

    @commands.command(name="userinfo", aliases=["memberinfo", "ui", "mi", "info"])
    async def user_info_prefix(self, ctx: commands.Context, target: Optional[Member]):
        """Shows information about a user. (Prefix Command)"""
        target = target or ctx.author
        embed = self._create_user_info_embed(target)
        await ctx.send(embed=embed)

    @app_commands.command(name="user-info", description="Shows information about a user.")
    async def user_info_slash(self, interaction: discord.Interaction, target: Optional[Member]):
        """Shows information about a user. (Slash Command)"""
        target = target or interaction.user
        embed = self._create_user_info_embed(target)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(InfoCog(bot))