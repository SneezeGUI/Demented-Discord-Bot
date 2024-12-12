import discord
from discord.ext import commands
from data.keep_alive import keep_alive
import asyncio
import os
import random
import requests
from prompts import compliments
from prompts import insults
from discord import FFmpegPCMAudio
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer


description = '''Demented Bot'''

client = commands.Bot(command_prefix = "!", case_insensitive=True, intents=discord.Intents.all())
client.remove_command("help")

RNG_THRESHOLD = 3

@client.event
async def on_member_join(ctx,member):
    await ctx.send( f'Hi {member.name}, welcome to cul-Ahem server')
    await member.dm_channel.send(
        f'Hi {member.name}, welcome to cul-Ahem server'
    )

@client.event
async def on_ready():
  print("Bot is online!")
  await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='Sneeze'))

#COGS ====>

modules = ['slash', 'meme', 'events', 'info', 'fun',]
try:
    for module in modules:
        client.load_extension('cogs.' + module)
        print(f'Loaded: {module}.')
except Exception as e:
    print(f'Error loading {module}: {e}')

print('Bot.....Activated')


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Please type in a valid command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required arguments. Please type in *all* arguments.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have the necessary permissions.")
    elif isinstance(error, commands.CommandOnCooldown):
      msg = "You are on cooldown, please try again in {:.2f}s".format(error.retry_after)
      await ctx.send(msg)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send('Well here I am!')
        break


# Function to play a sound
async def join_and_play(voice_channel, sound_file):
    try:
        if os.path.exists(sound_file):
            print("Sound file found!")
            voice_client = await voice_channel.connect()
            print("Bot has joined the voice channel.")
            # source = FFmpegPCMAudio(sound_file, options="-filter:a 'volume=2.0'")
            source = FFmpegPCMAudio(sound_file)
            voice_client.play(source)

            while voice_client.is_playing():
                await asyncio.sleep(1)

            await voice_client.disconnect()
            print("Bot has left the voice channel.")
        else:
            print("Sound file not found!")
    except Exception as e:
        print(f"Error joining or playing sound: {e}")


async def send_insult(ctx, message, use_api=True):
    print('insulting ' + ctx.author.name)
    # set bot to typing
    await ctx.channel.trigger_typing()


    # wait for bot to finish typing
    await asyncio.sleep(5)

    if use_api:
        insult = "{} " + requests.get('https://evilinsult.com/generate_insult.php?lang=en&type=plaintext').text
    else:
        insult = "{} " + random.choice(insults)
    await ctx.reply(insult.format (f'@{ctx.author.mention}'))


async def send_compliment(ctx):
    print('Complimenting ' + ctx.author.name)
    # set bot to typing
    await ctx.channel.trigger_typing()   # await message.channel.typing()   CANT USE AWAIT AND TYPING TOGETHER ANYMORE

    # wait for bot to finish typing
    await asyncio.sleep(5)

    compliment = "{} " + random.choice(compliments)
    await ctx.reply(compliment.format(f'@{ctx.author.mention}'))



async def analyze(user_input):
    sia = SentimentIntensityAnalyzer()
    return sia.polarity_scores(user_input)


@client.event
async def on_message(message):
    if message.author == client.user or message.author == 415380635343912972:
        return

    rng = random.randrange(0, 100, 1)
    print(rng)
    await asyncio.sleep(1)

    rng_threshold = RNG_THRESHOLD

    # Check if bot is mentioned in message
    if client.user.mentioned_in(message) or 'demented' in message.content.lower() or 'demented 2.0' in message.content.lower():
        if 'join' in message.content.lower() and message.author.voice:
            voice_channel = message.author.voice.channel
            # play a random sound from the bot sounds folder
            sound_file = random.choice(os.listdir('bot_sounds'))
            sound_file = 'bot_sounds/' + sound_file
 
            await join_and_play(voice_channel, sound_file)
            return
        sentiment = await analyze(message.content)
        print(sentiment)
        if sentiment['compound'] >= 0.25:
            await send_compliment(message)
        elif sentiment['compound'] < 0.25:
            use_insult_api = rng >= rng_threshold / 2
            await send_insult(message, use_insult_api)
        return

    # bot was not mentioned, so we just use rng now
    if rng < rng_threshold:
        use_insult_api = rng >= rng_threshold / 2
        await send_insult(message, use_insult_api)

keep_alive()
client.run('token')
