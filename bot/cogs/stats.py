# stats.py

from discord.ext import commands
from discord import app_commands, Embed, Interaction, Member
from typing import Optional, List

from bot.helpers.api import api, PlayerStat
from bot.helpers.errors import CustomError
from bot.helpers.utils import align_text


class StatsCog(commands.Cog, name="Stats"):
    def __init__(self, bot):
        self.bot = bot

    def playerstat_template(self, playerstat: PlayerStat) -> Embed:
        """"""
        embed = Embed()
        embed.add_field(name='Rating', value=str(
            playerstat.rating), inline=False)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='Kills', value=str(playerstat.kills))
        embed.add_field(name='Assists', value=str(playerstat.assists))
        embed.add_field(name='Deaths', value=str(playerstat.deaths))
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='K/D Ratio', value=str(playerstat.kdr))
        embed.add_field(name='Headshots', value=str(playerstat.headshots))
        embed.add_field(name='HS Percent', value=str(playerstat.hsp))
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='3 K/R', value=str(playerstat.k3))
        embed.add_field(name='4 K/R', value=str(playerstat.k4))
        embed.add_field(name='5 K/R', value=str(playerstat.k5))
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='Wins', value=str(playerstat.wins))
        embed.add_field(name='Played', value=str(playerstat.played))
        embed.add_field(name='Win Percent', value=str(playerstat.win_percent))
        return embed

    @app_commands.command(name="stats", description="Show your stats")
    @app_commands.describe(target="Target user to show their stats")
    async def stats(self, interaction: Interaction, target: Optional[Member]):
        """"""
        await interaction.response.defer()
        user = target or interaction.user
        playerstat = await api.get_playerstat(user, self.bot)
        if not playerstat:
            raise CustomError(
                f"No stats were recorded for user {user.mention}")

        embed = self.playerstat_template(playerstat)
        embed.set_author(name=user.display_name, icon_url=user.avatar)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="Show top player stats")
    async def leaderboard(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        leaderboard = await api.get_leaderboard(interaction.guild.members)
        leaderboard.sort(key=lambda u: (u.rating), reverse=True)
        leaderboard = leaderboard[:10]

        # Generate leaderboard text
        data = [['Player'] + [player.name for player in leaderboard],
                ['Kills'] + [str(player.kills) for player in leaderboard],
                ['Deaths'] + [str(player.deaths) for player in leaderboard],
                ['Assists'] + [str(player.assists)
                               for player in leaderboard],
                ['Played'] + [str(player.played)
                              for player in leaderboard],
                ['Wins'] + [str(player.wins) for player in leaderboard],
                ['Rating'] + [str(player.rating) for player in leaderboard]]
        data[0] = [name if len(name) < 11 else name[:8] +
                   '...' for name in data[0]]  # Shorten long names
        widths = list(map(lambda x: len(max(x, key=len)), data))
        aligns = ['left', 'center', 'center',
                  'center', 'center', 'center', 'center']
        z = zip(data, widths, aligns)
        formatted_data = [list(map(lambda x: align_text(
            x, width, align), col)) for col, width, align in z]
        # Transpose list for .format() string
        formatted_data = list(map(list, zip(*formatted_data)))

        description = '```ml\n    {}  {}  {}  {}  {}  {}  {} \n'.format(
            *formatted_data[0])

        for rank, player_row in enumerate(formatted_data[1:], start=1):
            description += ' {}. {}  {}  {}  {}  {}  {}  {} \n'.format(
                rank, *player_row)

        description += '```'

        embed = Embed(title='Leaderboard', description=description)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
