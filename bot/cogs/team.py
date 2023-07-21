# team.py

from discord.ext import commands
from discord import app_commands, Interaction


class TeamCog(commands.Cog):
    """"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create-team", description="Create a new team")
    @app_commands.describe(name="Team name")
    async def create_team(self, interaction: Interaction, name: str):
        """"""
        await interaction.response.defer()
