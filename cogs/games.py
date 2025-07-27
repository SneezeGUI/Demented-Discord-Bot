# C:/Development/Projects/Demented-Discord-Bot/cogs/games.py

import logging
from random import choice
import discord
from datetime import datetime
import html
from discord.ext import commands
from data.session_manager import cached_http_get
from data.helper_functions import GameData, timed_command

logger = logging.getLogger('demented_bot.games')

# Constants for colors
COLOR_RED = 0xEF2928
COLOR_BLUE = 0x0094E6


class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['t'], help="Gives a prompt for the game of truth!", brief="Game of Truths!")
    @commands.cooldown(1, 2.5, commands.BucketType.user)
    @timed_command("Truth command execution")
    async def truth(self, ctx: commands.Context):
        """Get a truth question."""
        truths = GameData.get("truths")
        if not truths:
            await ctx.send("Sorry, I couldn't find any truth questions right now.")
            return
        response = f"**Truth:** {choice(truths)}"
        await ctx.send(response)

    @commands.command(aliases=['d'], help="Gives a prompt for the game of dares!", brief="Game of Daress!")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @timed_command("Dare command execution")
    async def dare(self, ctx: commands.Context):
        """Get a dare."""
        dares = GameData.get("dares")
        if not dares:
            await ctx.send("Sorry, I couldn't find any dare questions right now.")
            return
        response = f"**Dare:** {choice(dares)}"
        await ctx.send(response)

    @commands.command(aliases=['neverhaveiever', 'nhie', 'ever', 'n'],
                      help="Gives questions for the age old game of never have I ever! ", brief="Never Have I ever -")
    @commands.cooldown(1, 2.5, commands.BucketType.user)
    @timed_command("Never command execution")
    async def never(self, ctx: commands.Context):
        """Get a never have I ever question."""
        nhie = GameData.get("nhie")
        if not nhie:
            await ctx.send("Sorry, I couldn't find any 'Never Have I Ever' questions right now.")
            return
        response = f"**Never have I ever** {choice(nhie)}"
        await ctx.send(response)

    @commands.command(aliases=['tot', 'tt'], help="Gives you two options to choose from", brief="This Or That game.")
    @commands.cooldown(1, 2.5, commands.BucketType.user)
    @timed_command("This or That command execution")
    async def thisorthat(self, ctx: commands.Context):
        """Get a this or that question."""
        tot = GameData.get("tot")
        if not tot:
            await ctx.send("Sorry, I couldn't find any 'This or That' questions right now.")
            return
        response = choice(tot)

        message = []
        if ':' in response:
            split = response.split(':')
            message.append(f"**{split[0]}**")
            tort = split[1].strip()
        else:
            tort = response
        message.append(f"🔴 {tort.replace(' or ', ' **OR** ')} 🔵")

        embed = discord.Embed(
            color=choice((COLOR_RED, COLOR_BLUE)),
            timestamp=datetime.utcnow(),
            description='\n'.join(message)
        )

        sent_embed = await ctx.send(embed=embed)
        await sent_embed.add_reaction("🔴")
        await sent_embed.add_reaction("🔵")

    @commands.command(aliases=['wyr', 'rather'], help="Gets you a would you rather question!",
                      brief="Would you rather?")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @timed_command("Would You Rather command execution")
    async def wouldyourather(self, ctx: commands.Context):
        """Get a would you rather question."""
        try:
            # CORRECTED: Handles single return value
            result = await cached_http_get('http://either.io/questions/next/1/', ttl_seconds=600)

            if not result:
                await ctx.send("Sorry, couldn't fetch a 'Would You Rather' question. Try again later.")
                return

            question_data = result['questions'][0]

            option1, option2 = question_data['option_1'].capitalize(), question_data['option_2'].capitalize()
            option1_total, option2_total = int(question_data['option1_total']), int(question_data['option2_total'])
            option_total = option1_total + option2_total or 1  # Avoid division by zero
            comments = question_data['comment_total']
            title, desc, url = question_data['title'], question_data['moreinfo'], question_data['short_url']

            embed = discord.Embed(
                title=title,
                url=url,
                color=COLOR_RED if (option1_total > option2_total) else COLOR_BLUE,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name='Would You Rather',
                value=f"🔴 `({(option1_total / option_total * 100):.1f}%)` {option1}\n🔵 `({(option2_total / option_total * 100):.1f}%)` {option2}",
                inline=False
            )
            if desc: embed.add_field(name="More Info", value=desc, inline=False)
            embed.set_footer(text=f"either.io • 💬 {comments}")
            sent_embed = await ctx.send(embed=embed)
            await sent_embed.add_reaction("🔴")
            await sent_embed.add_reaction("🔵")
        except Exception as e:
            logger.error(f"Error in wouldyourather command: {e}")
            await ctx.send("An error occurred while fetching the question. Please try again.")

    @commands.command(name='button', aliases=['wyp', 'willyoupressthebutton'],
                      help="If you are given two absurd choices, which one would you choose?",
                      brief="Will you press the button?")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @timed_command("Will You Press command execution")
    async def button(self, ctx: commands.Context):
        """Get a will you press the button question."""
        try:
            # CORRECTED: Handles single return value
            result = await cached_http_get(
                'https://api2.willyoupressthebutton.com/api/v2/dilemma',
                method="post",
                ttl_seconds=600
            )

            if not result:
                await ctx.send("Sorry, couldn't fetch a 'Will You Press the Button' question. Try again later.")
                return

            dilemma = result['dilemma']

            txt1, txt2 = html.unescape(dilemma['txt1']), html.unescape(dilemma['txt2'])
            will_press, wont_press = int(dilemma['yes']), int(dilemma['no'])
            press_total = (will_press + wont_press) or 1  # Avoid division by zero
            q_id = dilemma['id']
            url = f"https://willyoupressthebutton.com/{q_id}"

            embed = discord.Embed(
                title="Press the button?",
                url=url,
                color=COLOR_RED if (will_press > wont_press) else COLOR_BLUE,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name='Will you press the button if...',
                value=f"{txt1}\n**but...**\n{txt2}",
                inline=False
            )
            embed.add_field(
                name='Options',
                value=f"🔴 `({(will_press / press_total * 100):.1f}%)` I will press the button.\n🔵 `({(wont_press / press_total * 100):.1f}%)` I won't press the button.",
                inline=False
            )
            embed.set_footer(text="willyoupressthebutton.com")
            sent_embed = await ctx.send(embed=embed)
            await sent_embed.add_reaction("🔴")
            await sent_embed.add_reaction("🔵")
        except Exception as e:
            logger.error(f"Error in button command: {e}")
            await ctx.send("An error occurred while fetching the question. Please try again.")


async def setup(bot):
    await bot.add_cog(GamesCog(bot))
    