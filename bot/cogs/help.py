import discord
from discord.ext import commands
from paginator import Paginator

from bot.bot import G5Bot


class Help(commands.Cog):

    def __init__(self, bot: G5Bot):
        self.bot = bot

    @discord.app_commands.command(name='help', description='List of bot commands')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def help(self, interaction: discord.Interaction):
        """"""
        await interaction.response.defer(ephemeral=True)
        pages = []
        all_commands = await self.bot.tree.fetch_commands()

        for cog_name, cog in self.bot.cogs.items():
            if cog_name in ['Help', 'Logger']:
                continue
            embed = discord.Embed(title=cog_name + ' Commands', color=0x02b022)
            cog_commands = cog.get_app_commands()
            for cmd in cog_commands:
                for c in all_commands:
                    if c.name == cmd.name:
                        embed.add_field(name=c.mention,
                                        value=c.description, inline=False)
            pages.append({
                'label': f"{cog_name} Commands",
                'content': embed
            })

        paginator = Paginator(interaction, pages)
        await paginator.start(embeded=True, quick_navigation=len(pages) <= 25, followup=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
