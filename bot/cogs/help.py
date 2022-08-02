# help.py

from discord.ext import commands

from ..utils import Utils
from ..resources import G5

AUTHOR = 'TheBO$$#2967'
AUTHOR_ICON_URL = 'https://images.discordapp.net/avatars/389758324691959819/8888d88c6a8ca46de247882c8c0dcff2.png?size=64'


class HelpCog(commands.Cog):
    """ Handles everything related to the help menu. """

    def __init__(self):
        """ Set attributes and remove default help command. """
        G5.bot.remove_command('help')

    @commands.command(brief=Utils.trans('help-brief'))
    async def help(self, ctx):
        """ Generate and send help embed based on the bot's commands. """
        description = "__**Basic Info:**__\n" \
                      "_**G5** is a Discord bot to manage CS:GO matches on your own CS:GO servers_\n\n" \
                      "__**Commands List:**__"
        embed = G5.bot.embed_template(description=description)
        prefix = G5.bot.command_prefix
        prefix = prefix[0] if prefix is not str else prefix

        for cog in G5.bot.cogs:  # Uset bot.cogs instead of bot.commands to control ordering in the help embed
            for cmd in G5.bot.get_cog(cog).get_commands():
                if cmd.usage:  # Command has usage attribute set
                    embed.add_field(
                        name=f'**{prefix}{cmd.usage}**', value=f'_{cmd.brief}_', inline=False)
                else:
                    embed.add_field(
                        name=f'**{prefix}{cmd.name}**', value=f'_{cmd.brief}_', inline=False)
        embed.set_thumbnail(url=G5.bot.user.avatar_url_as(size=128))
        embed.set_footer(
            text=f'Kindly developed by {AUTHOR}',
            icon_url=AUTHOR_ICON_URL
        )
        await ctx.message.reply(embed=embed)
