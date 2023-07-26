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

    async def validate_join_team(self, user: Member, guild: Guild,
                                 team_role: Role)-> Tuple[TeamModel, UserModel]:
        """"""
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model or not user_model.steam:
            raise CustomError(f"You must be linked to {'join' if team_role else 'create'} a team.")

        team_model = await db.get_team_by_role(team_role, self.bot)
        if not team_model:
            raise CustomError("Team not found!")
        team_users = await db.get_team_users(team_model.id, guild)

        if len(team_users) >= 6:
            raise CustomError(f"Team **{team_model.name}** is full.")
        
        user_team = await db.get_user_team(user.id, guild)
        if user_team:
            raise CustomError(f"You already belong to team **{user_team.name}**")
        
        return team_model, user_model

    @app_commands.command(name="create-team", description="Create a new team")
    @app_commands.describe(name="Team name")
    async def create_team(self, interaction: Interaction, name: str):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        team_name = name[:25]

        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model or not user_model.steam:
            raise CustomError(f"You must be linked to create a team.")

        user_team = await db.get_user_team(user.id, guild)
        if user_team:
            raise CustomError(f"You already belong to team **{user_team.name}**")
        
        dict_user = { user_model.steam: {
            'nickname': user.display_name,
            'captain': True
        }}
        team_id = await api.create_team(team_name, dict_user)

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

        embed = Embed(description=f"Team **{team_name}** created successfully")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="join-team", description="Join a team")
    @app_commands.describe(team_role="Team role mention")
    @app_commands.checks.cooldown(1, 300)
    async def join_team(self, interaction: Interaction, team_role: Role):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild

        team_model, user_model = await self.validate_join_team(user, guild, team_role)
        
        description = f"User {user.mention} wants to join your team **{team_model.name}**"
        embed = Embed(description=description)
        view = RequestJoinView(team_model, user)
        message = await interaction.followup.send(content=team_model.captain.mention, embed=embed, view=view, wait=True)
        await view.wait()

        if view.accepted is None:
            description = "Timeout! The join request was not accepted."
        elif view.accepted:
            team_model, user_model = await self.validate_join_team(user, guild, team_role)
            added = await api.add_team_member(team_model.id, user_model.steam, user.display_name)
            if added:
                await db.insert_team_users(team_model.id, [user])
                try:
                    await user.add_roles(team_model.role)
                except: pass
                description = f"{user.mention} You have joined team **{team_model.name}**."
            else:
                description = "Something went wrong in API request, please try again later."
        else:
            description = "Join team request rejected. Maybe next time!"

        embed.description = description
        await message.edit(embed=embed, view=None)
    
    @app_commands.command(name="leave-team", description="Leave a team")
    async def leave_team(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild

        user_team = await db.get_user_team(user.id, guild)
        if not user_team:
            raise CustomError("You are not belong to any team.")
        
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model or not user_model.steam:
            raise CustomError("You must be linked to leave your team.")
        
        removed = await api.remove_team_member(user_team.id, user_model.steam)
        if removed:
            await db.delete_team_users(user_team.id, [user])
            try:
                await user.remove_roles(user_team.role)
            except: pass
            description = f"You have been removed from team **{user_team.name}**."
            if user_team.captain:
                embed = Embed(description=f"User {user.mention} just left your team.")
                await interaction.channel.send(content=user_team.captain.mention, embed=embed)
        else:
            description = "Something went wrong on API request, please try again later."

        embed = Embed(description=description)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="kick-teammate", description="Kick a user from your team")
    @app_commands.describe(teammate="A user to be kicked from your team")
    async def kick_teammate(self, interaction: Interaction, teammate: Member):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild

        user_team = await db.get_user_team(user.id, guild)
        if not user_team or user_team.captain != user:
            raise CustomError("Only team captains can access this!")
        
        team_users = await db.get_team_users(user_team.id, guild)
        if teammate not in team_users:
            raise CustomError(f"User {teammate.mention} is not member of your team.")
        
        teammate_user_model = await db.get_user_by_discord_id(teammate.id, self.bot)
        if not teammate_user_model or not teammate_user_model.steam:
            raise CustomError(f"User {teammate.mention} is not linked")
        
        removed = await api.remove_team_member(user_team.id, teammate_user_model.steam)
        if removed:
            await db.delete_team_users(user_team.id, [teammate])
            try:
                await teammate.remove_roles(user_team.role)
            except: pass
            embed = Embed(description=f"You just kicked from team **{user_team.name}**.")
            await interaction.channel.send(content=teammate.mention, embed=embed)
            description = f"User {teammate.mention} has been removed from your team."
        else:
            description = "Something went wrong on API request, please try again later."

        embed = Embed(description=description)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="delete-team", description="Delete your team")
    async def delete_team(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild

        user_team = await db.get_user_team(user.id, guild)
        if not user_team or user_team.captain != user:
            raise CustomError("Only team captains can access this!")
        
        team_users = await db.get_team_users(user_team.id, guild)
        
        deleted = await api.delete_team(user_team.id)
        if deleted:
            await db.delete_team(user_team.id, guild)
            try:
                await user_team.role.delete()
            except: pass
            description = f"Your team **{user_team.name}** has been deleted."
            embed = Embed(description=description)
            teammate_mentions = ''.join(u.mention for u in team_users)
            await interaction.followup.send(content=teammate_mentions, embed=embed)
        else:
            description = "Something went wrong on API request, please try again later."
            await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TeamCog(bot))