import os
import discord
from discord.ext import commands
from data.keep_alive import keep_alive
import random
from dotenv import load_dotenv

load_dotenv()

description = '''Demented Bot'''
LISTENING_TO = ['Sneeze', 'the Voices', 'my Dad', 'your moms queefs', 'Davids Screams', 'children crying']

bot = commands.Bot(command_prefix="!", case_insensitive=True, intents=discord.Intents.all())
bot.remove_command("help")

bot_token= os.getenv('BOT_TOKEN')  # or a placeholder if needed, e.g. "YOUR_BOT_TOKEN_HERE"


@bot.event
async def on_member_join(ctx, member):
    await ctx.send(f'Hi {member.name}, welcome to cul-Ahem server')
    await member.dm_channel.send(f'Hi {member.name}, welcome to cul-Ahem server')


@bot.event
async def on_ready():
    print("Bot is online!")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(LISTENING_TO)))


@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send('Well here I am!')
        break


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


def main():
    modules = ['slash', 'meme', 'fun', 'info', 'events']
    for module in modules:
        bot.load_extension('cogs.' + module)
        print(f'Loaded: {module}.')
    print('Bot.....Activated')

    keep_alive()  # Make sure debug mode is off in keep_alive if you're using a Flask app
    bot.run(bot_token)  # Replace with your actual bot token as needed


if __name__ == '__main__':
    main()