import asyncio
import os
import random
import discord
import requests
from discord import FFmpegPCMAudio
from discord.ext import commands
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from bot import LISTENING_TO
from prompts import compliments
from prompts import insults

RNG_THRESHOLD = 3

class EventsCog(commands.Cog):
  def __init__(self, bot):
      self.bot = bot

  # Function to play a sound
  async def join_and_play(self, voice_channel, sound_file):
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

  async def send_insult(self, ctx, message, use_api=True):
      print('insulting ' + ctx.author.name)
      # set bot to typing
      await ctx.channel.trigger_typing()

      # wait for bot to finish typing
      await asyncio.sleep(5)
      # change listening to
      print('Status Updated')
      await self.bot.change_presence(
          activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(LISTENING_TO)))
      if use_api:
          insult = "{} " + requests.get('https://evilinsult.com/generate_insult.php?lang=en&type=plaintext').text
      else:
          insult = "{} " + random.choice(insults)
      await ctx.reply(insult.format(f'{ctx.author.mention}'))

  async def send_compliment(self, ctx):
      print('Complimenting ' + ctx.author.name)
      # set bot to typing
      await ctx.channel.trigger_typing()  # await message.channel.typing()   CANT USE AWAIT AND TYPING TOGETHER ANYMORE

      # wait for bot to finish typing
      await asyncio.sleep(5)
      # change listening to

      compliment = "{} " + random.choice(compliments)
      await ctx.reply(compliment.format(f'{ctx.author.mention}'))
      print('Status Updated')
      await self.bot.change_presence(
          activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(LISTENING_TO)))

  async def analyze(self, user_input):
      sia = SentimentIntensityAnalyzer()
      return sia.polarity_scores(user_input)

  @commands.Cog.listener()
  async def on_message(self, message):
      # if message.content.startswith("!"):

      if message.author == self.bot.user or message.author == 1314688956989964388:

          return

      rng = random.randrange(0, 100, 1)
      print(rng)
      print('Analyzing...')
      # await self.bot.change_presence(
      #     activity= discord.Activity(type= discord.ActivityType.listening, name=random.choice(LISTENING_TO)))
      await asyncio.sleep(1)

      rng_threshold = RNG_THRESHOLD

      # Check if bot is mentioned in message
      if self.bot.user.mentioned_in(message) or 'demented' in message.content.lower() or 'demented 2.0' in message.content.lower():
          if 'join' in message.content.lower() and message.author.voice:
              voice_channel = message.author.voice.channel
              # play a random sound from the bot sounds folder
              sound_file = random.choice(os.listdir('bot_sounds'))
              sound_file = 'bot_sounds/' + sound_file

              await self.join_and_play(voice_channel, sound_file)
              return
          sentiment = await self.analyze(message.content)
          print(sentiment)
          if sentiment['compound'] >= 0.25:
              await self.send_compliment(message)
          elif sentiment['compound'] < 0.25:
              use_insult_api = rng >= rng_threshold / 2
              await self.send_insult(message, use_insult_api)
          return

      # bot was not mentioned, so we just use rng now
      if rng < rng_threshold:
          use_insult_api = rng >= rng_threshold / 2
          await self.send_insult(message, use_insult_api)

def setup(bot):
    bot.add_cog(EventsCog(bot))