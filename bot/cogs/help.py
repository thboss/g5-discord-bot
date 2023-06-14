import discord
from discord.ext import commands


class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name='help', description='List of all commands')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def help(self, interaction: discord.Interaction):
        """"""
        command_list = await self.bot.tree.fetch_commands()
        command_dict = {}
        for command in command_list:
            command_dict[command.name] = command

        cog_commands = {}
        for cog in self.bot.cogs.values():
            if cog.qualified_name in ["Logger", "Help"]:
                continue
            cog_commands[cog.qualified_name] = []
            for command in cog.get_app_commands():
                cog_commands[cog.qualified_name].append(command.name)

        embed = discord.Embed(title='Help', color=0x02b022)
        embed.description = 'List of commands'
        embed.set_footer(
            text="Usage syntax: <required argument>, [optional argument]")

        for category, commands in cog_commands.items():
            embed.add_field(name=category, value=', '.join(
                [command_dict[i].mention for i in commands]), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
