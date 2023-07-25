# team.py

from discord.ext import commands
from discord import app_commands, Interaction, Embed, Role, Member, ButtonStyle, Guild
from discord.ui import View, Button, button

from typing import Tuple

from bot.helpers.models import TeamModel, UserModel
from bot.helpers.errors import CustomError
from bot.helpers.db import db
from bot.helpers.api import api


class RequestJoinView(View):
    """ A view that displays buttons for accept or reject joining a team. """

    def __init__(self, team: TeamModel, target_user: Member, timeout=20):
        super().__init__(timeout=timeout)
        self.team = team
        self.target_user = target_user
        self.accepted = None

    @button(label='Accept', style=ButtonStyle.green)
    async def _accept(self, interaction: Interaction, button: Button):
        self.accepted = True
        self.stop()

    @button(label='Reject', style=ButtonStyle.red)
    async def _reject(self, interaction: Interaction, button: Button):
        self.accepted = False
        self.stop()

    async def interaction_check(self, interaction: Interaction):
        if interaction.user != self.team.captain:
            await interaction.response.send_message(
                content="You are not allowed to interact with this!",
                ephemeral=True)
            return False
        return True


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
        team_name = name[:25]

        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model:
            raise CustomError("You must be linked to join a team.")

        user_team = await db.get_user_team(user.id, guild)
        if user_team:
            raise CustomError(f"You already have a team ({user_team.role.mention})")
        
        team_id = await api.create_team(team_name, [user])
        team_role = await guild.create_role(name="team_" + team_name)

        await db.insert_team({
            'id': team_id,
            'name': f'\'{team_name}\'',
            'guild': guild.id,
            'role': team_role.id,
            'captain': user.id
        })
        await db.insert_team_users(team_id, [user])
        await user.add_roles(team_role)

        embed = Embed(description=f"{team_role.mention} created successfully")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="join-team", description="Join a team")
    @app_commands.describe(team="Team role mention")
    async def join_team(self, interaction: Interaction, team: Role):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild

        target_team, user_model = await self.validate_join_team(user, team, guild)
        
        msg = f"User {user.mention} wants to join your team ({target_team.name})"
        embed = Embed(description=msg)
        view = RequestJoinView(target_team, user)
        message = await interaction.followup.send(content=target_team.captain.mention, embed=embed, view=view, wait=True)
        await view.wait()

        if view.accepted is None:
            embed = Embed(description="Timeout! The join request was not accepted.")
        elif view.accepted:
            target_team, user_model = await self.validate_join_team(user, team, guild)
            await api.add_team_member(target_team.id, user_model.steam, user.display_name)
            await db.insert_team_users(target_team.id, [user])
            embed = Embed(description=f"Congratulations! You have joined team **{target_team.name}**.")
        else:
            embed = Embed(description="Join team request rejected. Maybe next time!")

        await message.edit(embed=embed, view=None)

    async def validate_join_team(self, user: Member, team_role: Role, guild: Guild) -> Tuple[TeamModel, UserModel]:
        """"""
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model:
            raise CustomError("You must be linked to join a team.")

        team = await db.get_team_by_role(team_role, self.bot)
        if not team:
            raise CustomError("Team not found!")
        
        user_team = await db.get_user_team(user.id, guild)
        if user_team:
            raise CustomError(f"You already belong to team **{user_team.name}**")
        
        team_users = await db.get_team_users(team.id, guild)
        if len(team_users) >= 6:
            raise CustomError(f"Team **{team.name}** is already full.")
        
        return team, user_model
        

async def setup(bot):
    await bot.add_cog(TeamCog(bot))