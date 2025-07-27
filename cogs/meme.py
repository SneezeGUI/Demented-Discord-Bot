# C:/Development/Projects/Demented-Discord-Bot/cogs/meme.py

import discord
from discord.ext import commands
import random
import logging
from data.session_manager import cached_http_get

logger = logging.getLogger('demented_bot.meme')


class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_reddit_post(self, subreddit: str):
        """
        Helper function to fetch a random hot post from a subreddit.
        Returns a tuple: (discord.Embed, error_message_string).
        One of the two will always be None.
        """
        url = f'https://www.reddit.com/r/{subreddit}/hot.json'
        # CORRECTED: Handles single return value from cached_http_get
        data = await cached_http_get(url, ttl_seconds=300)

        if not data or 'error' in data or not data.get('data', {}).get('children'):
            logger.warning(f"Failed to get valid data from r/{subreddit}")
            return None, f"Could not fetch posts from r/{subreddit}. It might be private, banned, or have no posts."

        posts = [
            p['data'] for p in data['data']['children']
            if not p['data'].get('stickied', False)
               and p['data'].get('url', '').endswith(('.jpg', '.jpeg', '.png', '.gif'))
        ]

        if not posts:
            return None, f"Couldn't find any image posts on r/{subreddit} right now."

        post = random.choice(posts)
        image_url = post.get('url')
        title = post.get('title', f"From r/{subreddit}")
        permalink = f"https://www.reddit.com{post.get('permalink', '')}"

        embed = discord.Embed(
            title=title,
            url=permalink,
            color=discord.Color.orange()
        )
        embed.set_image(url=image_url)
        embed.set_footer(text=f"👍 {post.get('ups', 0)} | 💬 {post.get('num_comments', 0)}")

        return embed, None

    @commands.command(help="Posts a meme from a specified subreddit.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reddit(self, ctx: commands.Context, subreddit: str):
        """Posts a hot meme from a given subreddit."""
        async with ctx.typing():
            embed, error_msg = await self._get_reddit_post(subreddit)
            if error_msg:
                await ctx.send(error_msg)
            else:
                await ctx.send(embed=embed)

    @commands.command(name="meme", help="Posts a meme from r/memes.", aliases=['memes'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def meme_command(self, ctx: commands.Context):
        """Posts a meme from r/memes."""
        await self.reddit(ctx, subreddit="memes")

    @commands.command(name="dank", help="Posts a meme from r/dankmemes.", aliases=['dankmeme'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dank_command(self, ctx: commands.Context):
        """Posts a meme from r/dankmemes."""
        await self.reddit(ctx, subreddit="dankmemes")


async def setup(bot):
    await bot.add_cog(Meme(bot))