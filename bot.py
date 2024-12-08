import discord
from discord.ext import commands
from data.keep_alive import keep_alive

description = '''Practice Bot'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = commands.Bot(command_prefix = "!", case_insensitive=False)
client.remove_command("help")

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

modules = ['slash' , 'meme']
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

keep_alive()
client.run('token')
