# team.py

from discord.ext import commands
from discord import app_commands, Interaction, Embed

from bot.helpers.errors import CustomError
from bot.helpers.db import db
from bot.helpers.api import api

class TeamCog(commands.Cog):
    """"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create-team", description="Create a new team")
    @app_commands.describe(name="Team name")
    async def create_team(self, interaction: Interaction, name: str):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        team_name = 'team_' + name[:25]
        in_team = await db.get_user_team(user.id, guild)
        if in_team:
            raise CustomError("You already have a team")
        
        team_id = await api.create_team(team_name, [user])
        team_role = await guild.create_role(name=team_name)

        await db.insert_team({
            'id': team_id,
            'name': f'\'{team_name}\'',
            'guild': guild.id,
            'role': team_role.id,
            'captain': user.id
        })
        await db.insert_team_users(team_id, [user])

        embed = Embed(description=f"{team_role.mention} created successfully")
        await interaction.followup.send(embed=embed)
        

async def setup(bot):
    await bot.add_cog(TeamCog(bot))