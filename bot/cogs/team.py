# team.py

from discord.ext import commands
from discord import app_commands, Interaction, Embed, Role, Member, ButtonStyle, Guild, SelectOption
from discord.interactions import Interaction
from discord.ui import View, Button, Select, button, select

from typing import Tuple, List, Literal

from bot.helpers.models import TeamModel, UserModel
from bot.helpers.errors import CustomError
from bot.helpers.db import db
from bot.helpers.api import api
from bot.messages import ReadyView
from .lobby import SERIES_CHOICES, GAME_MODE_CHOICES


class DropDownTeamPlayers(Select):
    """"""
    def __init__(self, options: List[SelectOption], min_values: int, max_values: int):
        super().__init__(placeholder="Choose your team players to participate in the match",
                         min_values=min_values, max_values=max_values, options=options)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        self.view.selected_users = self.values
        await self.view.stop()


class DropDownTeamPlayersView(View):
    """"""

    def __init__(self, author: Member, users: List[Member], team_capacity: int, timeout=60):
        super().__init__(timeout=timeout)
        self.author = author
        self.users = users
        self.selected_users = []
        options = [SelectOption(label=user.display_name, value=user.id) for user in users]
        self.add_item(DropDownTeamPlayers(options, team_capacity, team_capacity))
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                content="You are not allowed to interact with this!",
                ephemeral=True)
            return False
        return True


class Confirm(View):
    """ A view that displays two buttons for accept or reject an action. """

    def __init__(self, team: TeamModel, timeout=60):
        super().__init__(timeout=timeout)
        self.team = team
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
        view = Confirm(team_model)
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
        embed = Embed()

        user_team = await db.get_user_team(user.id, guild)
        if not user_team or user_team.captain != user:
            raise CustomError("Only team captains can access this!")
        
        team_users = await db.get_team_users(user_team.id, guild)
        
        status_code = await api.delete_team(user_team.id)
        if status_code < 400 or status_code == 404:
            await db.delete_team(user_team.id, guild)
            try:
                await user_team.role.delete()
            except: pass
            description = f"Your team **{user_team.name}** has been deleted."
            embed.description  =description
            teammate_mentions = ''.join(u.mention for u in team_users)
            await interaction.followup.send(content=teammate_mentions, embed=embed)
        else:
            embed.description = "Something went wrong on API request, please try again later."
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="challenge", description="Start a new match against another team")
    @app_commands.describe(team_role="Team role mention", team_capacity="Number of players per team")
    @app_commands.choices(
        series=SERIES_CHOICES,
        game_mode=GAME_MODE_CHOICES,
    )
    @app_commands.checks.cooldown(1, 120)
    async def challenge(
        self, interaction: Interaction,
        team_role: Role,
        series: app_commands.Choice[str],
        game_mode: app_commands.Choice[str],
        team_capacity: int,
    ):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        embed = Embed()

        team1_model = await db.get_user_team(user.id, guild)
        if not team1_model or team1_model.captain != user:
            raise CustomError("Only team captains can access this.")
        
        team2_model = await db.get_team_by_role(team_role, self.bot)
        if not team2_model:
            raise CustomError(f"Team {team_role.mention} not found.")
        
        if team1_model.id == team2_model.id:
            raise CustomError("You cannot challenge your team!")
        
        team1_users = await db.get_team_users(team1_model.id, guild)
        team2_users = await db.get_team_users(team2_model.id, guild)
        
        dropdown = DropDownTeamPlayersView(user, team1_users, team_capacity)
        message = await interaction.followup.send(view=dropdown, wait=True)
        await dropdown.wait()
        if not dropdown.selected_users:
            embed.description = f"Timeout! Captain {team1_model.captain.mention} haven't selected their team in time!"
            await message.edit(embed=embed, view=None)
            return
        
        team1_users = list(filter(lambda x: str(x.id) in dropdown.selected_users, team1_users))
        embed.description = f"Team **{team1_model.name}** wants to challenge your team **{team2_model.name}**"
        mentions_msg = await interaction.channel.send(content=team2_model.captain.mention)
        view = Confirm(team2_model)
        await message.edit(embed=embed, view=view)
        await view.wait()
        await mentions_msg.delete()

        if view.accepted is None:
            embed.description = "Timeout! The challenge was not accepted."
            await message.edit(embed=embed, view=None)
        elif view.accepted:
            dropdown = DropDownTeamPlayersView(team2_model.captain, team2_users, team_capacity)
            await message.edit(embed=None, view=dropdown)
            await dropdown.wait()
            if not dropdown.selected_users:
                embed.description = f"Timeout! Captain {team2_model.captain.mention} haven't selected their team in time!"
                await message.edit(embed=embed, view=None)
                return
            team2_users = list(filter(lambda x: str(x.id) in dropdown.selected_users, team2_users))
            unreadied_users = []
            match_users = team1_users + team2_users
            menu = ReadyView(match_users)
            ready_users = await menu.ready_up(message)
            unreadied_users = set(match_users) - ready_users

            if unreadied_users:
                embed.description = "Not everyone was ready"
                await message.edit(embed=embed, view=None)
            else:
                embed.description = "Starting match setup..."
                await message.edit(embed=embed, view=None)
                match_cog = self.bot.get_cog("Match")
                map_pool = await db.get_guild_maps(guild)
                await match_cog.start_match(
                    guild,
                    message,
                    map_pool,
                    game_mode=game_mode.value,
                    series=series.value,
                    team1_model=team1_model,
                    team2_model=team2_model)
        else:
            embed.description = "Challenge rejected. Maybe next time!"
            await message.edit(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(TeamCog(bot))