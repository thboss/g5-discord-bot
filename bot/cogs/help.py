import discord
from discord.ext import commands

from bot.bot import G5Bot


class Help(commands.Cog):

    def __init__(self, bot: G5Bot):
        self.bot = bot

    @discord.app_commands.command(name='help', description='List of bot commands')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def help(self, interaction: discord.Interaction):
        """"""
        embed = discord.Embed(title='Commands List', color=0x02b022)
        commands = await self.bot.tree.fetch_commands()

        for cmd in commands:
            embed.add_field(name=cmd.mention,
                            value=cmd.description, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
