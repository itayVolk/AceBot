import discord
from discord.ext import commands

bot = commands.Bot(command_prefix=('!', '.'), description='Bot made by RUNIE')

extensions = (
	'cogs.commands.commands',
	'cogs.autohotkey.autohotkey',
)

@bot.event
async def on_ready():
	await bot.change_presence(game=discord.Game(name='autohotkey.com', type=1, url='http://autohotkey.com/'))

	if __name__ == '__main__':
		print(f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
		for extension in extensions:
			bot.load_extension(extension)
	print(f'Successfully connected!')

@bot.before_invoke
async def before_any_command(ctx):
	print('\n{} in {}:\n{}'.format(ctx.message.author.name, ctx.guild.name, ctx.message.content))

@bot.after_invoke
async def after_any_command(ctx):
	try:
		message = bot._connection._messages[-1]
	except:
		return
	if not message.author.id == ctx.bot.user.id:
		return
	split = message.content.split('\n')
	text = split[0]
	if len(split) > 1:
		text = text + "..."
	print('Result:\n' + text)


with open('lib/bot_token.txt', 'r') as f:
	bot.run(f.read())