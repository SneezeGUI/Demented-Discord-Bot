import discord
from discord.ext import commands
from data.keep_alive import keep_alive
import asyncio
import os
import random
import requests

description = '''Demented Bot'''

bot = commands.Bot(command_prefix = "!", case_insensitive=True, intents=discord.Intents.all())
bot.remove_command("help")

@bot.event
async def on_member_join(ctx,member):
    await ctx.send( f'Hi {member.name}, welcome to cul-Ahem server')
    await member.dm_channel.send(
        f'Hi {member.name}, welcome to cul-Ahem server'
    )

@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send('Well here I am!')
        break

@bot.event
async def on_ready():
  print("Bot is online!")
  await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='Sneeze'))

#COGS ====>
# modules = ['slash', 'games','events', 'fun', 'api', 'meme']
# def load_cogs():
#
#     try:
#         for module in modules:
#             bot.load_extension(f'cogs.' + module)
#             print(f'Loaded: {module}.')
#
#     except Exception as e:
#         print(f'Error loading {module}: {e}')
# print('Bot.....Activated')

modules = ['slash', 'meme', 'fun', 'info', 'events',]
try:
    for module in modules:
        bot.load_extension('cogs.' + module)
        print(f'Loaded: {module}.')
except Exception as e:
    print(f'Error loading {module}: {e}')

print('Bot.....Activated')

@bot.event
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

# async def main():
#     async with bot:
#         await load_cogs()
#         keep_alive()
#         await bot.start('token')
#
#
# asyncio.run(main())

keep_alive()
bot.run('token')
