# match.py

from discord.ext import commands, tasks
from discord import Embed, NotFound, app_commands, Member, Message, Interaction, Guild, SelectOption
from typing import Literal, List

from random import sample, shuffle
from datetime import datetime
import asyncio

from bot.helpers.api import api, Match, MapStat, Server
from bot.helpers.db import db
from bot.helpers.models import GuildModel, TeamModel, MatchModel, MapModel
from bot.bot import G5Bot
from bot.helpers.errors import CustomError, APIError
from bot.helpers.configs import Config
from bot.views import VetoView, PickTeamsView, DropDownView, ConfirmView, ReadyView
from .lobby import SERIES_CHOICES, CAPACITY_CHOICES, GAME_MODE_CHOICES


class MatchCog(commands.Cog, name="Match"):
    """"""

    def __init__(self, bot: G5Bot):
        self.bot = bot

    @app_commands.command(name="create-match", description="Setup a new match between two teams.")
    @app_commands.choices(
        capacity=CAPACITY_CHOICES,
        series=SERIES_CHOICES,
        game_mode=GAME_MODE_CHOICES,
    )
    @app_commands.describe(
        capacity="Capacity of the lobby",
        series="Number of maps per match",
        game_mode="Set game mode"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_match(
        self,
        interaction: Interaction,
        capacity: app_commands.Choice[int],
        series: app_commands.Choice[str],
        game_mode: app_commands.Choice[str]
    ):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        channel = interaction.channel
        team_capacity = int(capacity.value // 2)
        embed = Embed()

        guild_maps = await db.get_guild_maps(guild, game_mode.value)
        if len(guild_maps) < 7:
            raise CustomError("No maps found in the server. Please add **atleast 7** maps using command `/add-map`.")

        placeholder = "Select map pool"
        options = [SelectOption(label=m.display_name, value=m.map_id) for m in guild_maps]
        max_maps = len(guild_maps) if series.value == "bo1" else 7
        dropdown = DropDownView(user, placeholder, options, 7, max_maps)
        message = await interaction.followup.send(view=dropdown, wait=True)
        await dropdown.wait()

        if not dropdown.selected_options:
            embed.description = "Timeout! You haven't selected maps in time!"
            await message.edit(embed=embed, view=None)
            return
        
        map_pool = list(filter(lambda x: str(x.map_id) in dropdown.selected_options, guild_maps))

        guild_teams = await db.get_guild_teams(guild)
        if len(guild_teams) < 2:
            embed.description = "No teams found in the server."
            await message.edit(embed=embed, view=None)
            return
        
        placeholder = "Choose two teams"
        options = [SelectOption(label=f"Team {team.name}", value=team.id) for team in guild_teams]
        dropdown = DropDownView(user, placeholder, options, 2, 2)
        await message.edit(view=dropdown)
        await dropdown.wait()

        if not dropdown.selected_options:
            embed.description = "Timeout! You haven't selected teams in time!"
            await message.edit(embed=embed, view=None)
            return
        
        team1_model = await db.get_team_by_id(int(dropdown.selected_options[0]), self.bot)
        team2_model = await db.get_team_by_id(int(dropdown.selected_options[1]), self.bot)
        
        team1_users = await db.get_team_users(team1_model.id, guild)
        mention = await channel.send(team1_model.captain.mention)
        placeholder = "Choose your team players"
        options = [SelectOption(label=user.display_name, value=user.id) for user in team1_users]
        dropdown = DropDownView(team1_model.captain, placeholder, options, team_capacity, team_capacity)
        await message.edit(view=dropdown)
        await dropdown.wait()
        await mention.delete()

        if not dropdown.selected_options:
            embed.description = f"Timeout! Captain {team1_model.captain.mention} has not selected their team in time!"
            await message.edit(embed=embed, view=None)
            return

        team1_users = list(filter(lambda x: str(x.id) in dropdown.selected_options, team1_users))

        team2_users = await db.get_team_users(team2_model.id, guild)
        mention = await channel.send(team2_model.captain.mention)
        placeholder = "Choose your team players"
        options = [SelectOption(label=user.display_name, value=user.id) for user in team2_users]
        dropdown = DropDownView(team2_model.captain, placeholder, options, team_capacity, team_capacity)
        await message.edit(view=dropdown)
        await dropdown.wait()
        await mention.delete()

        if not dropdown.selected_options:
            embed.description = f"Timeout! Captain {team2_model.captain.mention} has not selected their team in time!"
            await message.edit(embed=embed, view=None)
            return

        team2_users = list(filter(lambda x: str(x.id) in dropdown.selected_options, team2_users))
        
        match_users = team1_users + team2_users
        mention = await channel.send(''.join(u.mention for u in match_users))
        ready_view = ReadyView(match_users, message)
        await message.edit(embed=ready_view._embed_ready(), view=ready_view)
        await ready_view.wait()
        unreadied_users = set(match_users) - ready_view.ready_users
        await mention.delete()

        if unreadied_users:
            embed.description = "Not everyone was ready"
            await message.edit(embed=embed, view=None)
            return

        embed.description = "Starting match setup..."
        await message.edit(embed=embed, view=None)
        await self.start_match(
            guild,
            message,
            map_pool,
            game_mode=game_mode.value,
            series=series.value,
            team1_model=team1_model,
            team2_model=team2_model
        )

    @app_commands.command(name="challenge", description="Start a new match vs a team from your choice")
    @app_commands.choices(
        capacity=CAPACITY_CHOICES,
        series=SERIES_CHOICES,
        game_mode=GAME_MODE_CHOICES,
    )
    @app_commands.describe(
        capacity="Capacity of the lobby",
        series="Number of maps per match",
        game_mode="Set game mode"
    )
    @app_commands.checks.cooldown(1, 300)
    async def challenge(
        self,
        interaction: Interaction,
        capacity: app_commands.Choice[int],
        series: app_commands.Choice[str],
        game_mode: app_commands.Choice[str]
    ):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        channel = interaction.channel
        team_capacity = int(capacity.value // 2)
        embed = Embed()

        team1_model = await db.get_user_team(user.id, guild)
        if not team1_model or team1_model.captain != user:
            raise CustomError("Only team captains can access this.")
        
        team1_match = await db.get_team_match(team1_model.id, guild)
        if team1_match:
            raise CustomError(f"Your team **{team1_model.name}** is already in match **#{team1_match.id}**")
        
        team1_users = await db.get_team_users(team1_model.id, guild)
        if len(team1_users) < team_capacity:
            raise CustomError(f"Your team **{team1_model.name}** has only {len(team1_users)} players.")

        guild_maps = await db.get_guild_maps(guild, game_mode.value)
        if len(guild_maps) < 7:
            raise CustomError("No maps found in the server.")

        placeholder = "Select map pool"
        options = [SelectOption(label=m.display_name, value=m.map_id) for m in guild_maps]
        max_maps = len(guild_maps) if series.value == "bo1" else 7
        dropdown = DropDownView(user, placeholder, options, 7, max_maps)
        message = await interaction.followup.send(view=dropdown, wait=True)
        await dropdown.wait()

        if not dropdown.selected_options:
            embed.description = f"Timeout! You haven't selected maps in time!"
            await message.edit(embed=embed, view=None)
            return
        
        map_pool = list(filter(lambda x: str(x.map_id) in dropdown.selected_options, guild_maps))

        guild_teams = await db.get_guild_teams(guild)
        guild_teams = [team for team in guild_teams if team.id != team1_model.id]
        if not guild_teams:
            embed.description = "No teams found in the server."
            await message.edit(embed=embed, view=None)
            return

        placeholder = "Choose a team to challenge"
        options = [SelectOption(label=f"Team {team.name}", value=team.id) for team in guild_teams]
        dropdown = DropDownView(user, placeholder, options, 1, 1)
        await message.edit(view=dropdown)
        await dropdown.wait()

        if not dropdown.selected_options:
            embed.description = "Timeout! You haven't selected a team in time!"
            await message.edit(embed=embed, view=None)
            return
        
        team2_model = await db.get_team_by_id(int(dropdown.selected_options[0]), self.bot)
        
        team2_match = await db.get_team_match(team2_model.id, guild)
        if team2_match:
            embed.description = f"Team **{team2_model.name}** is already in match **#{team2_match.id}**"
            await message.edit(embed=embed, view=None)
            return

        mention = await channel.send(team1_model.captain.mention)
        placeholder = "Choose your team players"
        options = [SelectOption(label=user.display_name, value=user.id) for user in team1_users]
        dropdown = DropDownView(user, placeholder, options, team_capacity, team_capacity)
        await message.edit(view=dropdown)
        await dropdown.wait()
        await mention.delete()

        if not dropdown.selected_options:
            embed.description = f"Timeout! Captain {team1_model.captain.mention} has not selected their team in time!"
            await message.edit(embed=embed, view=None)
            return
        
        team1_users = list(filter(lambda x: str(x.id) in dropdown.selected_options, team1_users))

        embed.description = f"Team **{team1_model.name}** wants to challenge your team **{team2_model.name}**"
        mention = await channel.send(team2_model.captain.mention)
        confirm = ConfirmView(team2_model.captain)
        await message.edit(embed=embed, view=confirm)
        await confirm.wait()
        await mention.delete()

        if confirm.accepted is None:
            embed.description = "Timeout! The challenge was not accepted."
            await message.edit(embed=embed, view=None)
        elif confirm.accepted:
            team2_users = await db.get_team_users(team2_model.id, guild)
            mention = await channel.send(team2_model.captain.mention)
            placeholder = "Choose your team players"
            options = [SelectOption(label=user.display_name, value=user.id) for user in team2_users]
            dropdown = DropDownView(team2_model.captain, placeholder, options, team_capacity, team_capacity)
            await message.edit(embed=None, view=dropdown)
            await dropdown.wait()
            await mention.delete()

            if not dropdown.selected_options:
                embed.description = f"Timeout! Captain {team2_model.captain.mention} has not selected their team in time!"
                await message.edit(embed=embed, view=None)
                return
    
            team2_users = list(filter(lambda x: str(x.id) in dropdown.selected_options, team2_users))
            match_users = team1_users + team2_users

            mention = await channel.send(''.join(u.mention for u in match_users))
            ready_view = ReadyView(match_users, message)
            await message.edit(embed=ready_view._embed_ready(), view=ready_view)
            await ready_view.wait()
            unreadied_users = set(match_users) - ready_view.ready_users
            await mention.delete()

            if unreadied_users:
                embed.description = "Not everyone was ready"
                await message.edit(embed=embed, view=None)
            else:
                embed.description = "Starting match setup..."
                await message.edit(embed=embed, view=None)
                map_pool = await db.get_guild_maps(guild, game_mode.value)
                await self.start_match(
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

    @app_commands.command(name="cancel-match", description="Cancel a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def cancel_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.cancel_match(match_id)
        embed = Embed(description=f"Match #{match_id} canceled successfully.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="restart-match", description="Restart a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.restart_match(match_id)
        embed = Embed(description=f"Match #{match_id} restarted successfully.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause-match", description="Pause a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def pause_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.pause_match(match_id)
        embed = Embed(description=f"Match #{match_id} paused successfully.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unpause-match", description="Unpause a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def unpause_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.unpause_match(match_id)
        embed = Embed(description=f"Match #{match_id} unpaused successfully.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="add-match-player", description="Add player to a live match")
    @app_commands.describe(match_id="Match ID", user="User to add them to the match", team="The team where player will be added")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_match_player(self, interaction: Interaction, match_id: int, user: Member, team: Literal["team1", "team2", "spec"]):
        """"""
        await interaction.response.defer()
        match_model = await db.get_match_by_id(match_id, self.bot)
        if not match_model:
            raise CustomError("Invalid match ID!")

        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model or not user_model.steam:
            raise CustomError(
                f"Unable to add {user.mention}! User is not linked.")

        user_lobby = await db.get_user_lobby(user.id, interaction.guild)
        if user_lobby:
            raise CustomError(f"Unable to add {user.mention}! User in lobby.")

        user_match = await db.get_user_match(user.id, interaction.guild)
        if user_match:
            raise CustomError(f"Unable to add {user.mention}! User in match.")

        if team == "team1":
            api_team = await api.get_team(match_model.team1_id)
            team_channel = match_model.team1_channel
            team_name = api_team.name
        elif team == "team2":
            api_team = await api.get_team(match_model.team2_id)
            team_channel = match_model.team2_channel
            team_name = api_team.name
        else:
            team_name = "spectator"

        await api.add_match_player(match_id, user_model.steam, user.display_name, team)
        await db.insert_match_users(match_id, [user])

        try:
            await team_channel.set_permissions(user, connect=True)
            await user.move_to(team_channel)
        except Exception as e:
            pass

        embed = Embed(
            description=f"Player {user.mention} added to match #{match_id}: Team {team_name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="remove-match-player", description="Remove player from a live match")
    @app_commands.describe(match_id="Match ID", user="User to remove from the match")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_match_player(self, interaction: Interaction, match_id: int, user: Member):
        """"""
        await interaction.response.defer()
        match_model = await db.get_match_by_id(match_id, self.bot)
        if not match_model:
            raise CustomError("Invalid match ID!")

        guild_model = await db.get_guild_by_id(interaction.guild.id, self.bot)

        user_match = await db.get_user_match(user.id, interaction.guild)
        if not user_match or user_match.id != match_id:
            raise CustomError(
                f"User {user.mention} is not in match #{match_id}")

        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model or not user_model.steam:
            raise CustomError(
                f"Unable to remove {user.mention}! User is not linked.")

        team1 = await api.get_team(match_model.team1_id)
        team2 = await api.get_team(match_model.team2_id)

        if user_model.steam in team1.auth_name.keys():
            target_team = team1
            team_channel = match_model.team1_channel
        elif user_model.steam in team2.auth_name.keys():
            target_team = team2
            team_channel = match_model.team2_channel
        else:
            target_team = None

        if not target_team:
            raise CustomError(
                f"User {user.mention} not in match #{match_id}")

        await api.remove_match_player(match_id, user_model.steam)
        await db.delete_match_user(match_id, user)

        try:
            await team_channel.set_permissions(user, connect=None)
            await user.move_to(guild_model.prematch_channel)
        except Exception as e:
            pass

        embed = Embed(
            description=f"Player {user.mention} removed from match #{match_id}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="replace-match-player", description="Replace player in a live match")
    @app_commands.describe(match_id="Match ID", current_user="User to remove from the match", new_user="User to add to the match")
    @app_commands.checks.has_permissions(administrator=True)
    async def replace_match_player(self, interaction: Interaction, match_id: int, current_user: Member, new_user: Member):
        """"""
        await interaction.response.defer()
        match_model = await db.get_match_by_id(match_id, self.bot)
        if not match_model:
            raise CustomError("Invalid match ID!")

        guild_model = await db.get_guild_by_id(interaction.guild.id, self.bot)

        current_user_model = await db.get_user_by_discord_id(current_user.id, self.bot)
        if not current_user_model or not current_user_model.steam:
            raise CustomError(
                f"Current user {current_user.mention} is not linked.")

        new_user_model = await db.get_user_by_discord_id(new_user.id, self.bot)
        if not new_user_model or not new_user_model.steam:
            raise CustomError(
                f"New user {new_user.mention} is not linked.")

        current_user_match = await db.get_user_match(current_user.id, interaction.guild)
        if not current_user_match or current_user_match.id != match_id:
            raise CustomError(
                f"Current user {current_user.mention} not in match #{match_id}")

        new_user_match = await db.get_user_match(new_user.id, interaction.guild)
        if new_user_match:
            raise CustomError(
                f"New user {new_user.mention} already in a match.")

        team1 = await api.get_team(match_model.team1_id)
        team2 = await api.get_team(match_model.team2_id)

        if current_user_model.steam in team1.auth_name.keys():
            target_team = team1
            team_channel = match_model.team1_channel
            team_str = 'team1'
        elif current_user_model.steam in team2.auth_name.keys():
            target_team = team2
            team_channel = match_model.team2_channel
            team_str = 'team2'
        else:
            target_team = None

        if not target_team:
            raise CustomError(
                f"Current user {current_user.mention} not in match #{match_id}")

        await api.remove_match_player(match_id, current_user_model.steam)
        await db.delete_match_user(match_id, current_user)

        await api.add_match_player(match_id, new_user_model.steam, new_user.display_name, team_str)
        await db.insert_match_users(match_id, [new_user])

        try:
            await team_channel.set_permissions(current_user, connect=None)
            await current_user.move_to(guild_model.prematch_channel)
        except Exception as e:
            pass

        try:
            await team_channel.set_permissions(new_user, connect=True)
            await new_user.move_to(team_channel)
        except Exception as e:
            pass

        embed = Embed(
            description=f"User {current_user.mention} replaced to {new_user.mention} in match #{match_id}")
        await interaction.followup.send(embed=embed)

    async def autobalance_teams(self, users: List[Member]):
        """ Balance teams based on players' avarage raitng. """
        try:
            leaderboard = await api.get_leaderboard(users)
        except Exception as e:
            return self.randomize_teams(users)

        stats_dict = dict(zip(leaderboard, users))
        players_stats = list(stats_dict.keys())
        players_stats.sort(key=lambda x: x.rating)

        # Balance teams
        team_size = len(players_stats) // 2
        team1_stats = [players_stats.pop()]
        team2_stats = [players_stats.pop()]

        while players_stats:
            if len(team1_stats) >= team_size:
                team2_stats.append(players_stats.pop())
            elif len(team2_stats) >= team_size:
                team1_stats.append(players_stats.pop())
            elif sum(p.rating for p in team1_stats) < sum(p.rating for p in team2_stats):
                team1_stats.append(players_stats.pop())
            else:
                team2_stats.append(players_stats.pop())

        team1_users = list(map(stats_dict.get, team1_stats))
        team2_users = list(map(stats_dict.get, team2_stats))
        return team1_users, team2_users

    async def pick_teams(self, message: Message, users: List[Member], captain_method: str):
        """"""
        teams_view = PickTeamsView(message, users)
        await teams_view.start(captain_method)
        await message.edit(embed=teams_view.create_teams_embed("Start teams pickings"), view=teams_view)
        await teams_view.wait()
        if teams_view.users_left:
            raise asyncio.TimeoutError
        return teams_view.teams[0], teams_view.teams[1]

    def randomize_teams(self, users: List[Member]):
        """"""
        temp_users = users.copy()
        shuffle(temp_users)
        team_size = len(temp_users) // 2
        team1_users = temp_users[:team_size]
        team2_users = temp_users[team_size:]
        return team1_users, team2_users

    def embed_match_info(self, match_stats: Match, game_server: Server = None, mapstats: List[MapStat] = []):
        """"""
        title = f"**{match_stats.team1_string}**  [{match_stats.team1_score}:{match_stats.team2_score}]  **{match_stats.team2_string}**"
        description = ''

        if game_server:
            description += game_server.connect_info

        for mapstat in mapstats:
            if mapstat.start_time:
                start_time = datetime.fromisoformat(
                    mapstat.start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")

                description += f"**Map {mapstat.map_number+1}:** {mapstat.map_name}\n" \
                    f"**Score:** {match_stats.team1_string}  [{mapstat.team1_score}:{mapstat.team2_score}]  " \
                    f"{match_stats.team2_string}\n**Start Time:** {start_time}\n"

            if mapstat.end_time:
                end_time = datetime.fromisoformat(
                    mapstat.end_time.replace("Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")
                description += f"**End Time:** {end_time}\n"
            description += '\n\n'

        description += f"[Match Info]({Config.base_url}/match/{match_stats.id})"

        embed = Embed(title=title, description=description)
        embed.set_author(
            name=f"{'🔴' if match_stats.end_time else '🟢'} Match #{match_stats.id}")
        embed.set_thumbnail(url=self.bot.avatar_url)
        if not mapstats and not match_stats.end_time:
            embed.set_footer(
                text="Server will close after 5 minutes if anyone doesn't join")
        return embed

    async def start_match(
        self,
        guild: Guild,
        message: Message,
        mpool: List[MapModel],
        game_mode: str='competitive',
        queue_users: List[Member]=[], 
        team_method: str='captains',
        map_method: str='veto',
        captain_method: str='rank',
        series: str='bo1',
        region: str='',
        team1_model: TeamModel=None,
        team2_model: TeamModel=None
    ):
        """"""
        is_pug = len(queue_users) > 0
        await asyncio.sleep(3)
        try:
            if not is_pug: # official match
                team1_captain = team1_model.captain
                team2_captain = team2_model.captain
                team1_name = team1_model.name
                team2_name = team2_model.name
                team1_id = team1_model.id
                team2_id = team2_model.id
                team1_users = await db.get_team_users(team1_id, guild)
                team2_users = await db.get_team_users(team2_id, guild)
            else: # pug match
                if team_method == 'captains' and len(queue_users) >= 4:
                    team1_users, team2_users = await self.pick_teams(message, queue_users, captain_method)
                elif team_method == 'autobalance' and len(queue_users) >= 4:
                    team1_users, team2_users = await self.autobalance_teams(queue_users)
                else:  # team_method is random
                    team1_users, team2_users = self.randomize_teams(queue_users)
                
                team1_users_model = await db.get_users(team1_users)
                team2_users_model = await db.get_users(team2_users)
                team1_captain = team1_users[0]
                team2_captain = team2_users[0]
                team1_name = team1_captain.display_name
                team2_name = team2_captain.display_name
                dict_team1_users = { user_model.steam: {
                    'name': user_model.user.display_name,
                    'captain': user_model.user == team1_captain,
                    'coach': False,
                } for user_model in team1_users_model}
                dict_team2_users = { user_model.steam: {
                    'name': user_model.user.display_name,
                    'captain': user_model.user == team2_captain,
                    'coach': False,
                } for user_model in team2_users_model}
                team1_id = await api.create_team(team1_name, dict_team1_users)
                team2_id = await api.create_team(team2_name, dict_team2_users)

            if map_method == 'veto':
                veto_view = VetoView(message, mpool, series, team1_captain, team2_captain)
                await message.edit(embed=veto_view.embed_veto(), view=veto_view)
                await veto_view.wait()
                if not veto_view.is_veto_done:
                    raise asyncio.TimeoutError
                maps_list = veto_view.maps_pick
            else:
                maps_list = sample(mpool, int(series[2]))

            str_maps = ' '.join(m.dev_name for m in maps_list)
            await message.edit(embed=Embed(description='Searching for available game servers...'), view=None)
            await asyncio.sleep(2)
            match_server = await self.find_match_server(region)
            await message.edit(embed=Embed(description='Setting up match on game server...'), view=None)
            await asyncio.sleep(2)

            match_id = await api.create_match(
                match_server.id,
                team1_id,
                team2_id,
                str_maps,
                len(team1_users + team2_users),
                game_mode,
                is_pug
            )

            await message.edit(embed=Embed(description='Setting up teams channels...'), view=None)
            category, team1_channel, team2_channel = await self.create_match_channels(
                match_id,
                team1_name,
                team2_name,
                team1_users,
                team2_users,
                guild
            )

            await db.insert_match({
                'id': match_id,
                'team1_id': team1_id,
                'team2_id': team2_id,
                'guild': guild.id,
                'channel': message.channel.id,
                'message': message.id,
                'category': category.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id
            })

            match_stats = await api.get_match(match_id)
            await db.insert_match_users(match_id, team1_users + team2_users)
            embed = self.embed_match_info(match_stats, match_server)

        except APIError as e:
            description = e.message
            self.bot.log_exception('API ERROR: ', e)
        except asyncio.TimeoutError:
            description = 'Setup took too long!'
        except ValueError as e:
            description = e
        except Exception as e:
            self.bot.log_exception('Unhandled exception in "cogs.match.start_match": ', e)
            description = 'Something went wrong! See logs for details'
        else:
            try:
                await message.edit(embed=embed, view=None)
            except Exception as e:
                pass

            if not self.check_live_matches.is_running():
                self.check_live_matches.start()

            return True

        # Delete the created teams from api if setup didn't complete
        if is_pug:
            try:
                await api.delete_team(team1_id)
            except Exception as e:
                self.bot.logger.warning(str(e))

            try:
                await api.delete_team(team2_id)
            except Exception as e:
                self.bot.logger.warning(str(e))

        embed = Embed(title="Match Setup Failed",
                      description=description, color=0xE02B2B)
        try:
            await message.edit(embed=embed, view=None)
        except Exception as e:
            pass

    async def find_match_server(self, region=None):
        """"""
        servers = await api.get_servers()

        for server in servers:
            if server.in_use:
                continue

            if region and server.flag != region:
                continue

            try:
                is_available = await api.is_server_available(server.id)
                if is_available:
                    return server
            except Exception as e:
                self.bot.log_exception('API ERROR: ', e)
                continue

        raise ValueError("No game server available.")

    async def create_match_channels(
        self,
        match_id: int,
        team1_name: str,
        team2_name: str,
        team1_users: List[Member],
        team2_users: List[Member],
        guild: Guild
    ):
        """"""
        match_catg = await guild.create_category_channel(f"Match #{match_id}")

        team1_channel = await guild.create_voice_channel(
            name=f"Team {team1_name}",
            category=match_catg
        )

        team2_channel = await guild.create_voice_channel(
            name=f"Team {team2_name}",
            category=match_catg
        )

        await team1_channel.set_permissions(guild.self_role, connect=True)
        await team2_channel.set_permissions(guild.self_role, connect=True)
        await team1_channel.set_permissions(guild.default_role, connect=False, read_messages=True)
        await team2_channel.set_permissions(guild.default_role, connect=False, read_messages=True)

        for user in team1_users:
            try:
                await team1_channel.set_permissions(user, connect=True)
                await user.move_to(team1_channel)
            except Exception as e:
                pass

        for user in team2_users:
            try:
                await team2_channel.set_permissions(user, connect=True)
                await user.move_to(team2_channel)
            except Exception as e:
                pass

        return match_catg, team1_channel, team2_channel

    async def finalize_match(self, match_model: MatchModel, guild_model: GuildModel):
        """"""
        match_players = await db.get_match_users(match_model.id, match_model.guild)
        match_channels = [
            match_model.team1_channel,
            match_model.team2_channel,
            match_model.category
        ]

        for user in match_players:
            try:
                await user.move_to(guild_model.prematch_channel)
            except Exception as e:
                pass

        for channel in match_channels:
            try:
                await channel.delete()
            except Exception as e:
                pass

        await db.delete_match(match_model.id)

    async def update_match_stats(self, match_model: MatchModel):
        """"""
        match_stats = None
        mapstats = []
        game_server = None
        message = None
        guild_model = await db.get_guild_by_id(match_model.guild.id, self.bot)

        if not match_model.text_channel:
            await self.finalize_match(match_model, guild_model)
            return

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
        except NotFound:
            pass

        try:
            match_stats = await api.get_match(match_model.id)
        except Exception as e:
            pass

        if not match_stats:
            await self.finalize_match(match_model, guild_model)
            return

        try:
            game_server = await api.get_server(match_stats.server_id)
        except Exception as e:
            pass

        try:
            mapstats = await api.get_mapstats(match_model.id)
        except Exception as e:
            pass

        if message:
            embed = self.embed_match_info(match_stats, game_server, mapstats)
            await message.edit(embed=embed)

        if not match_stats.end_time and not match_stats.cancelled and not match_stats.forfeit:
            return

        try:
            await message.delete()
        except (AttributeError, NotFound):
            pass

        if mapstats and not match_stats.cancelled:
            try:
                embed = self.embed_match_info(match_stats, mapstats=mapstats)
                await guild_model.results_channel.send(embed=embed)
            except Exception as e:
                pass

        await self.finalize_match(match_model, guild_model)

    @ tasks.loop(seconds=20.0)
    async def check_live_matches(self):
        """"""
        live_match = False
        for guild in self.bot.guilds:
            guild_matches = await db.get_guild_matches(guild)
            for match_model in guild_matches:
                live_match = True
                try:
                    await self.update_match_stats(match_model)
                except Exception as e:
                    self.bot.log_exception(
                        f'Uncaught exception when handling cogs.match.update_match_stats({match_model.id}):', e)
        if not live_match:
            self.check_live_matches.cancel()


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
