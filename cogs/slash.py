import discord
from discord.ext import commands
import asyncio
import random


class SlashCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize start_time here if you want to measure this Cog's uptime
        self.start_time = discord.utils.utcnow()

    # CLEAR
    @commands.has_permissions(manage_messages=True)
    @commands.slash_command(
        name='clear',
        description="Clears Messages",
    )
    async def clear(self, ctx, amount):
        await ctx.channel.purge(limit=int(amount))
        await ctx.respond("Cleared Messages")

    # CALL GAY
    @commands.slash_command(
        name='call-gay',
        description='calls user gay'
    )
    async def call_gay(self, ctx, member: discord.Member):
        await ctx.respond("About to lay the truth down...")
        await asyncio.sleep(1)
        await ctx.send(f"<@{member.id}> is Gay! lol")

    # ADD
    @commands.slash_command(
        name='add',
        description='adds two numbers'
    )
    async def add(self, ctx, left: int, right: int):
        """Adds two numbers together."""
        await ctx.respond(f"total is {left + right}")

    # SPAM
    @commands.slash_command(
        name="spam",
        description="Repeats a message multiple times.",
    )
    async def repeat(self, ctx, times: int, content='repeating...'):
        """Repeats a message multiple times."""
        await ctx.respond("Spamming...")
        for _ in range(times):
            await ctx.send(content)

    # KICK
    @commands.slash_command(
        name='kick',
        description="Kicks a member off the server"
    )
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        try:
            await member.send("You have been kicked for the reasons of " + reason)
        except:
            await ctx.respond("The member has their DM's off")
        await member.kick(reason=reason)
        await ctx.respond(f"{member.mention} was kicked - Reason: " + reason)

    # BAN
    @commands.slash_command(
        name='ban',
        description="Bans a member from the server"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.ban(reason=reason)
        await ctx.respond(f"{member.mention} was Banned! ")

    # UNBAN
    @commands.slash_command(
        name='unban',
        description="Unbans a member from the server"
    )
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member):
        banned_users = await ctx.guild.bans()  # Await the ban list
        member_name = member
        async for banned_entry in banned_users:
            user = banned_entry.user
            if user.name == member_name:
                await ctx.guild.unban(user)
                await ctx.send(f"{member_name} has been unbanned!")
                return
        await ctx.send(member + " was not found.")

    # MUTE
    @commands.slash_command(
        name='mute',
        description="Mutes a member"
    )
    @commands.has_permissions(kick_members=True)
    async def mute(self, ctx, member: discord.Member):
        muted_role = ctx.guild.get_role(1315394620259176510)
        await member.add_roles(muted_role)
        await ctx.respond(member.mention + " has been muted")

    # UNMUTE
    @commands.slash_command(
        name='unmute',
        description="Unmutes a member"
    )
    @commands.has_permissions(kick_members=True)
    async def unmute(self, ctx, member: discord.Member):
        unmuted_role = ctx.guild.get_role(1315394620259176510)
        await member.remove_roles(unmuted_role)
        await ctx.respond(member.mention + " has been unmuted")

    # PING
    @commands.slash_command(
        name="ping",
        description="Returns the bot's latency"
    )
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.respond(f"Pong! Latency is {latency}ms.")

    # USER INFO
    @commands.slash_command(
        name="user-info",
        description="Shows information about a user."
    )
    async def user_info(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(
            title=f"{member}'s Information",
            color=discord.Color.green()
        )
        embed.add_field(name="Display Name", value=member.display_name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        await ctx.respond(embed=embed)

    # AVATAR
    @commands.slash_command(
        name="avatar",
        description="Shows a user's avatar."
    )
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(
            title=f"{member.display_name}'s Avatar",
            color=discord.Color.random()
        )
        embed.set_image(url=member.avatar.url if member.avatar else None)
        await ctx.respond(embed=embed)

    # 8-BALL
    @commands.slash_command(
        name="8ball",
        description="Ask the magical 8-ball a question."
    )
    async def _8ball(self, ctx, *, question: str):
        responses = [
            "Yes.", "No.", "Maybe.", "Definitely!",
            "Ask again later.", "Not sure.", "Absolutely not."
        ]
        await ctx.respond(f"🎱 Question: {question}\n🎱 Answer: {random.choice(responses)}")

    # CHOOSE
    @commands.slash_command(
        name="choose",
        description="Let the bot make a decision for you."
    )
    async def choose(self, ctx, *choices: str):
        if len(choices) < 2:
            await ctx.respond("Please provide at least two choices.")
        else:
            await ctx.respond(f"I choose: {random.choice(choices)}")

    # UPTIME
    @commands.slash_command(
        name="uptime",
        description="Shows the bot's uptime."
    )
    async def uptime(self, ctx):
        now = discord.utils.utcnow()
        delta = now - self.start_time  # Use self.start_time instead of self.bot.start_time
        days, hours, minutes = delta.days, (delta.seconds // 3600), (delta.seconds // 60) % 60
        await ctx.respond(f"Bot Uptime: {days}d {hours}h {minutes}m")

    # FLIP
    @commands.slash_command(
        name="flip",
        description="Flips a coin."
    )
    async def flip(self, ctx):
        outcome = random.choice(["Heads", "Tails"])
        await ctx.respond(f"The coin landed on: {outcome}")

    # MEME
    @commands.slash_command(
        name="meme",
        description="Sends a random meme."
    )
    async def meme(self, ctx):
        meme_url = "https://i.imgflip.com/4t0m5.jpg"
        embed = discord.Embed(title="Here's a meme for you!", color=discord.Color.blurple())
        embed.set_image(url=meme_url)
        await ctx.respond(embed=embed)

    # POLL
    @commands.slash_command(
        name="poll",
        description="Create a poll with reactions."
    )
    async def poll(self, ctx, question: str, option_1: str, option_2: str):
        embed = discord.Embed(
            title=f"Poll: {question}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Option 1", value=f"🔵 {option_1}")
        embed.add_field(name="Option 2", value=f"🔴 {option_2}")
        message = await ctx.respond(embed=embed)
        msg = await message.original_response()
        await msg.add_reaction("🔵")
        await msg.add_reaction("🔴")


    #################################################
    #             NEW 20 SLASH COMMANDS             #
    #################################################

    # 1. ROLL
    @commands.slash_command(
        name="roll",
        description="Roll a random number between 1 and a specified max (default 100)."
    )
    async def roll(self, ctx, maximum: int = 100):
        result = random.randint(1, maximum)
        await ctx.respond(f"🎲 You rolled a {result} out of {maximum}!")

    # 2. REMIND
    @commands.slash_command(
        name="remind",
        description="Set a reminder for yourself."
    )
    async def remind(self, ctx, time_in_seconds: int, *, reminder: str):
        await ctx.respond(f"⏰ Reminder set for {time_in_seconds} seconds. I'll let you know!")
        await asyncio.sleep(time_in_seconds)
        await ctx.send(f"{ctx.author.mention}, here's your reminder: {reminder}")

    # 3. TIMER
    @commands.slash_command(
        name="timer",
        description="Starts a countdown timer in seconds."
    )
    async def timer(self, ctx, seconds: int):
        if seconds <= 0:
            await ctx.respond("Please specify a positive number of seconds.")
            return
        await ctx.respond(f"⏳ Timer started for {seconds} seconds.")
        await asyncio.sleep(seconds)
        await ctx.send(f"⏰ Time's up, {ctx.author.mention}!")

    # 4. JOKE
    @commands.slash_command(
        name="joke",
        description="Tells a random joke."
    )
    async def joke(self, ctx):
        jokes = [
            "Why do bicycles fall over? They are two-tired!",
            "I'm reading a book about anti-gravity. It's impossible to put down!",
            "Did you hear about the restaurant on the moon? Great food, but no atmosphere."
        ]
        await ctx.respond(random.choice(jokes))

    # 5. SERVER-STATS
    @commands.slash_command(
        name="server-stats",
        description="Shows a quick overview of the server's statistics."
    )
    async def server_stats(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title=f"{guild.name} Stats", color=discord.Color.blue())
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Member Count", value=guild.member_count, inline=True)
        embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await ctx.respond(embed=embed)

    # 6. HUG
    @commands.slash_command(
        name="hug",
        description="Give a hug to another user."
    )
    async def hug(self, ctx, member: discord.Member):
        await ctx.respond(f"{ctx.author.mention} gives a warm hug to {member.mention}! 🤗")

    # 7. SLAP
    @commands.slash_command(
        name="slap",
        description="Slap a user in a playful manner."
    )
    async def slap(self, ctx, member: discord.Member):
        await ctx.respond(f"{ctx.author.mention} just slapped {member.mention}! Ouch! 🖐")

    # 8. SAY
    @commands.slash_command(
        name="say",
        description="Make the bot say something on your behalf."
    )
    async def say(self, ctx, *, text: str):
        await ctx.respond(text)

    # 9. QUOTE
    @commands.slash_command(
        name="quote",
        description="Send a random motivational quote."
    )
    async def quote(self, ctx):
        quotes = [
            "Believe you can and you're halfway there.",
            "You miss 100% of the shots you don't take.",
            "Success is not final, failure is not fatal: it is the courage to continue that counts."
        ]
        await ctx.respond(random.choice(quotes))

    # 10. AFK
    @commands.slash_command(
        name="afk",
        description="Set your AFK status."
    )
    async def afk(self, ctx, *, reason: str = "AFK"):
        await ctx.respond(f"{ctx.author.mention} is now AFK. Reason: {reason}")

    # 11. BANLIST
    @commands.slash_command(
        name="banlist",
        description="Displays a list of banned users."
    )
    async def banlist(self, ctx):
        # Retrieve all bans as a list
        bans = [ban_entry async for ban_entry in ctx.guild.bans()]  # Consume the BanIterator
        # Check if the ban list is empty
        if not bans:
            await ctx.respond("There are no bans in this server.")
        else:
            # Build a list of banned users and send it
            banned_users = [f"{ban.user} (ID: {ban.user.id})" for ban in bans]
            await ctx.respond("• " + "\n• ".join(banned_users))

    # 12. DM
    @commands.slash_command(
        name="dm",
        description="Send a DM to a specified user."
    )
    async def dm(self, ctx, member: discord.Member, *, content: str):
        try:
            await member.send(content)
            await ctx.respond(f"DM sent to {member.mention}")
        except discord.Forbidden:
            await ctx.respond(f"I couldn't DM {member.mention}. They might have DMs disabled.")

    # 13. MOCK
    @commands.slash_command(
        name="mock",
        description="Alternates uppercase and lowercase in the provided text."
    )
    async def mock(self, ctx, *, text: str):
        mocked_text = "".join(random.choice([char.lower(), char.upper()]) for char in text)
        await ctx.respond(mocked_text)

    # 14. SHUFFLE
    @commands.slash_command(
        name="shuffle",
        description="Shuffles the provided list of words."
    )
    async def shuffle_words(self, ctx, words: str):
        word_list = list(words)
        random.shuffle(word_list)
        shuffled_text = ", ".join(word_list)
        await ctx.respond(f"Shuffled words: {shuffled_text}")

    # 15. CALC
    @commands.slash_command(
        name="calc",
        description="Evaluates a simple arithmetic expression."
    )
    async def calc(self, ctx, expression: str):
        try:
            result = eval(expression)
            if not isinstance(result, (int, float)):
                raise ValueError("Expression must be numeric.")
            await ctx.respond(f"The result of `{expression}` is `{result}`.")
        except:
            await ctx.respond("Invalid expression. Please use basic arithmetic.")

    # 16. CLAPIFY
    @commands.slash_command(
        name="clapify",
        description="Inserts the 👏 emoji between each word of the provided text."
    )
    async def clapify(self, ctx, *, text: str):
        clap_text = " 👏 ".join(text.split())
        await ctx.respond(clap_text)

    # 17. REVERSE
    @commands.slash_command(
        name="reverse",
        description="Reverses the given text."
    )
    async def reverse_text(self, ctx, *, text: str):
        reversed_str = text[::-1]
        await ctx.respond(f"Reversed: {reversed_str}")

    # 18. INSULT
    @commands.slash_command(
        name="insult",
        description="Sends a random playful insult."
    )
    async def insult(self, ctx, member: discord.Member):
        insults = [
            "You're as bright as a black hole, and twice as dense!",
            "I’d agree with you but then we’d both be wrong.",
            "If I wanted to kill myself, I'd climb your ego and jump to your IQ!"
        ]
        await ctx.respond(f"{member.mention}, {random.choice(insults)}")

    # 19. TABLEFLIP
    @commands.slash_command(
        name="tableflip",
        description="Flips a table in style!"
    )
    async def tableflip(self, ctx):
        await ctx.respond("(╯°□°）╯︵ ┻━┻")

    # 20. PAT
    @commands.slash_command(
        name="pat",
        description="Gently pat another user."
    )
    async def pat(self, ctx, member: discord.Member):
        await ctx.respond(f"{ctx.author.mention} gently pats {member.mention} on the head. 😊")


def setup(bot):
    bot.add_cog(SlashCog(bot))
