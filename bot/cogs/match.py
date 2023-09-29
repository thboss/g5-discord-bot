# match.py

from discord.ext import commands, tasks
from discord.errors import HTTPException
from discord import Embed, app_commands, Member, Message, Interaction, Guild, SelectOption, Role, PermissionOverwrite
from typing import Literal, List, Optional

from random import sample, shuffle
from datetime import datetime
import asyncio

from bot.helpers.api import api, Match, MapStat, Server, Season
from bot.helpers.db import db
from bot.helpers.models import GuildModel, TeamModel, MatchModel
from bot.bot import G5Bot
from bot.helpers.errors import CustomError, APIError
from bot.helpers.configs import Config
from bot.views import VetoView, PickTeamsView, DropDownView, ConfirmView, ReadyView
from .lobby import SERIES_CHOICES, CAPACITY_CHOICES, GAME_MODE_CHOICES


class MatchCog(commands.Cog, name="Match"):
    """"""

    def __init__(self, bot: G5Bot):
        self.bot = bot

    async def select_team_participants(self, team_model: TeamModel, capacity: int, interaction: Interaction) -> List[Member]:
        """"""
        team_match = await db.get_team_match(team_model.id, interaction.guild)
        if team_match:
            raise CustomError(f"Team **{team_model.name}** is already in match **#{team_match.id}**")
        
        team_users = await db.get_team_users(team_model.id, interaction.guild)
        if len(team_users) < capacity:
            raise CustomError(f"Team **{team_model.name}** has only {len(team_users)} players.")

        placeholder = "Choose your team players"
        options = [SelectOption(label=user.display_name, value=user.id) for user in team_users]
        dropdown = DropDownView(team_model.captain, placeholder, options, capacity, capacity)
        await interaction.edit_original_response(content=team_model.captain.mention, view=dropdown)
        await self.bot.notify(team_model.captain, channel=interaction.channel)
        await dropdown.wait()

        if not dropdown.selected_options:
            raise CustomError(f"Timeout! Captain {team_model.captain.mention} has not selected their team in time!")

        return list(filter(lambda x: str(x.id) in dropdown.selected_options, team_users))
    
    async def select_mpool(self, user: Member, game_mode: str, series: str, interaction: Interaction) -> List[str]:
        """"""
        placeholder = "Select map pool"
        all_maps = Config.maps[game_mode]
        options = [
            SelectOption(
                label=display_name,
                value=map_name
            ) for map_name, display_name in all_maps.items()
        ]
        max_maps = len(all_maps) if series == "bo1" else 7
        dropdown = DropDownView(user, placeholder, options, 7, max_maps)
        await interaction.edit_original_response(content=user.mention, view=dropdown)
        await self.bot.notify(user, channel=interaction.channel)
        await dropdown.wait()

        if not dropdown.selected_options:
            raise CustomError("Timeout! You haven't selected maps in time!")
        
        return list(filter(lambda x: x in dropdown.selected_options, all_maps.keys()))
    
    async def setup_teams_match(
        self,
        team1_model: TeamModel,
        team2_model: TeamModel,
        capacity: int,
        interaction: Interaction,
        series: Literal["bo1", "bo2", "bo3"],
        game_mode: Literal["competitive", "wingman"],
        author: Member,
        season_id: int=None
    ):
        """"""
        embed = Embed()
        map_pool = await self.select_mpool(author, game_mode, series, interaction)
        team1_users = await self.select_team_participants(team1_model, capacity, interaction)
        team2_users = await self.select_team_participants(team2_model, capacity, interaction)

        embed.add_field(name=f"Team {team1_model.name}", value="\n".join(u.mention for u in team1_users))
        embed.add_field(name=f"Team {team2_model.name}", value="\n".join(u.mention for u in team2_users))
        embed.add_field(name="Map Pool", value="\n".join(Config.maps[game_mode][m] for m in map_pool))
        message = await interaction.edit_original_response(embed=embed, view=None)
        await asyncio.sleep(3)
        
        match_users = team1_users + team2_users
        ready_view = ReadyView(match_users, interaction.channel)
        await ready_view.start()
        await ready_view.wait()
        unreadied_users = set(match_users) - ready_view.ready_users

        if unreadied_users:
            raise CustomError("Not everyone was ready")

        embed.clear_fields()
        embed.description = "Starting match setup..."
        message = await interaction.edit_original_response(embed=embed, view=None)
        match_started = await self.start_match(
            interaction.guild,
            message,
            map_pool,
            game_mode=game_mode,
            series=series,
            team1_model=team1_model,
            team2_model=team2_model,
            season_id=season_id
        )

        if match_started:
            match_model = await db.get_team_match(team1_model.id, interaction.guild)
            embed.description = f"{team1_model.role.mention} [Click here]({match_model.team1_channel.jump_url}) to join your team channel"
            await interaction.channel.send(embed=embed)
            embed.description = f"{team2_model.role.mention} [Click here]({match_model.team2_channel.jump_url}) to join your team channel"
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="create-match", description="Setup a new match between two teams.")
    @app_commands.choices(
        capacity=CAPACITY_CHOICES,
        series=SERIES_CHOICES,
        game_mode=GAME_MODE_CHOICES,
    )
    @app_commands.describe(
        capacity="Capacity of the lobby",
        series="Number of maps per match",
        game_mode="Set game mode",
        team1="Mention team1",
        team2="Mention team2",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_match(
        self,
        interaction: Interaction,
        team1: Role,
        team2: Role,
        capacity: app_commands.Choice[int],
        series: app_commands.Choice[str],
        game_mode: app_commands.Choice[str],
        season_id: Optional[int]
    ):
        """"""
        await interaction.response.defer()
        user = interaction.user
        team_capacity = int(capacity.value // 2)

        team1_model = await db.get_team_by_role(team1, self.bot)
        if not team1_model:
            raise CustomError(f"Team {team1.mention} not found")
        
        team2_model = await db.get_team_by_role(team2, self.bot)
        if not team2_model:
            raise CustomError(f"Team {team2.mention} not found")
        
        if season_id:
            season = await api.get_season(season_id)
            if not season:
                raise CustomError(f"Season #{season_id} not found.")
        
        await self.setup_teams_match(
            team1_model,
            team2_model,
            team_capacity,
            interaction,
            series.value,
            game_mode.value,
            user,
            season_id
        )

    @app_commands.command(name="challenge", description="Start a new match vs a team from your choice")
    @app_commands.choices(
        capacity=CAPACITY_CHOICES,
        series=SERIES_CHOICES,
        game_mode=GAME_MODE_CHOICES,
    )
    @app_commands.describe(
        team="Mention team role",
        capacity="Capacity of the lobby",
        series="Number of maps per match",
        game_mode="Set game mode"
    )
    @app_commands.checks.cooldown(1, 300)
    async def challenge(
        self,
        interaction: Interaction,
        team: Role,
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

        team2_model = await db.get_team_by_role(team, self.bot)
        if not team2_model:
            raise CustomError(f"Team {team.mention} not found.")
        
        if team1_model.id == team2_model.id:
            raise CustomError("Opps! You can't challenge your team.")

        embed.description = f"Team **{team1_model.name}** wants to challenge your team **{team2_model.name}**"
        confirm = ConfirmView(team2_model.captain)
        await interaction.edit_original_response(content=team2_model.captain.mention, embed=embed, view=confirm)
        await self.bot.notify(team2_model.captain, channel=channel)
        await confirm.wait()

        if confirm.accepted is None:
            raise CustomError("Timeout! The challenge was not accepted.")

        if not confirm.accepted:
            raise CustomError("Challenge rejected. Maybe next time!")

        await self.setup_teams_match(
            team1_model,
            team2_model,
            team_capacity,
            interaction,
            series.value,
            game_mode.value,
            user
        )

    @app_commands.command(name="cancel-match", description="Cancel a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def cancel_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        success, resp_msg = await api.cancel_match(match_id)
        if not success:
            raise APIError(resp_msg)

        embed = Embed(description=f"Match #{match_id} canceled successfully.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="forfeit-match", description="Forfeit a live match")
    @app_commands.describe(match_id="Match ID", winner="Choose either Team1 or Team2 to be the winner.")
    @app_commands.checks.has_permissions(administrator=True)
    async def forfeit_match(self, interaction: Interaction, match_id: int, winner: Literal["team1", "team2"]):
        """"""
        await interaction.response.defer()
        success, resp_msg = await api.forfeit_match(match_id, winner[4])
        if not success:
            raise APIError(resp_msg)

        description=f"Match #{match_id} has been forfeitted successfully."
        embed = Embed(description=description)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="restart-match", description="Restart a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        success, resp_msg = await api.restart_match(match_id)
        if not success:
            raise APIError(resp_msg)

        embed = Embed(description=f"Match #{match_id} restarted successfully.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause-match", description="Pause a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def pause_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        success, resp_msg = await api.pause_match(match_id)
        if not success:
            raise APIError(resp_msg)

        embed = Embed(description=f"Match #{match_id} paused successfully.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unpause-match", description="Unpause a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def unpause_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        success, resp_msg = await api.unpause_match(match_id)
        if not success:
            raise APIError(resp_msg)

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

        success, resp_msg = await api.add_match_player(match_id, user_model.steam, user.display_name, team)
        if not success:
            raise APIError(resp_msg)

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

        success, resp_msg = await api.remove_match_player(match_id, user_model.steam)
        if not success:
            raise APIError(resp_msg)

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
        await message.edit(embed=teams_view.embed_teams_pick("Start teams pickings"), view=teams_view)
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

    def embed_match_info(
        self,
        match_stats: Match,
        game_server: Server=None,
        mapstats: List[MapStat]=[],
        season: Season=None
    ):
        """"""
        title = f"**{match_stats.team1_string}**  [{match_stats.team1_score}:{match_stats.team2_score}]  **{match_stats.team2_string}**"
        description = ''

        if game_server:
            description += f'Server: `connect {game_server.ip_string}:{game_server.port}`\n\n' \
                           f'GOTV: `connect {game_server.ip_string}:{game_server.gotv_port}`\n\n'

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

        author_name = f"{'🔴' if match_stats.end_time else '🟢'} Match #{match_stats.id}"
        if match_stats.is_pug:
            author_name += " [PUG]"
        else:
            author_name += " [Official]"
        if season:
            author_name += f" [Season: {season.name}]"
        embed.set_author(name=author_name)

        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        if not mapstats and not match_stats.end_time:
            embed.set_footer(
                text="Server will close after 5 minutes if anyone doesn't join")
        return embed

    async def start_match(
        self,
        guild: Guild,
        message: Message,
        mpool: List[str],
        game_mode: str='competitive',
        queue_users: List[Member]=[], 
        team_method: str='captains',
        map_method: str='veto',
        captain_method: str='rank',
        series: str='bo1',
    ):
        """"""
        await asyncio.sleep(3)
        try:
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
            match_players = [ {
                'steam_id_64': u.steam,
                'team': 'team1' if u in team1_users_model else 'team2'
            } for u in team1_users_model + team2_users_model]

            if map_method == 'veto':
                veto_view = VetoView(message, mpool, series, team1_captain, team2_captain, game_mode)
                await message.edit(embed=veto_view.embed_veto(), view=veto_view)
                await veto_view.wait()
                maps_list = veto_view.maps_pick
            else:
                maps_list = sample(mpool, int(series[2]))

            await message.edit(embed=Embed(description='Searching for available game servers...'), view=None)
            await asyncio.sleep(2)

            game_server = await self.find_match_server()

            await message.edit(embed=Embed(description='Setting up match on game server...'), view=None)
            await asyncio.sleep(2)

            spectators = await db.get_spectators(guild)
            for spec in spectators:
                if spec.user not in team1_users and spec.user not in team2_users:
                    match_players.append({'steam_id_64': spec.steam, 'team': 'spectator'})

            api_match = await api.create_match(
                game_server.id,
                maps_list[0],
                team1_name,
                team2_name,
                match_players
            )

            await message.edit(embed=Embed(description='Setting up teams channels...'), view=None)
            category, team1_channel, team2_channel = await self.create_match_channels(
                api_match.id,
                team1_name,
                team2_name,
                team1_users,
                team2_users,
                guild
            )

            await db.insert_match({
                'id': api_match.id,
                'guild': guild.id,
                'channel': message.channel.id,
                'message': message.id,
                'category': category.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id
            })

            await db.insert_match_users(api_match.id, team1_users + team2_users)
            embed = self.embed_match_info(api_match, game_server)

        except APIError as e:
            description = e.message
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

        embed = Embed(title="Match Setup Failed",
                      description=description, color=0xE02B2B)
        try:
            await message.edit(embed=embed, view=None)
        except Exception as e:
            pass

    async def find_match_server(self):
        """"""
        game_servers = await api.get_game_servers()

        for game_server in game_servers:
            if not game_server.on:
                continue
            return game_server

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
        team1_channel, team2_channel = None, None
        team1_overwrites = {u: PermissionOverwrite(connect=True) for u in team1_users}
        team1_overwrites[guild.default_role] = PermissionOverwrite(connect=False)
        team2_overwrites = {u: PermissionOverwrite(connect=True) for u in team2_users}
        team2_overwrites[guild.default_role] = PermissionOverwrite(connect=False)

        try:
            team1_channel = await guild.create_voice_channel(
                name=f"Team {team1_name}",
                category=match_catg,
                overwrites=team1_overwrites
            )
        except HTTPException as e:
            self.bot.logger.warning(e)
            if e.code == 50035:
                team1_channel = await guild.create_voice_channel(
                    name=f"Team 1",
                    category=match_catg,
                    overwrites=team1_overwrites
                )
        
        try:
            team2_channel = await guild.create_voice_channel(
                name=f"Team {team2_name}",
                category=match_catg,
                overwrites=team2_overwrites
            )
        except HTTPException as e:
            self.bot.logger.warning(e)
            if e.code == 50035:
                team2_channel = await guild.create_voice_channel(
                    name=f"Team 2",
                    category=match_catg,
                    overwrites=team2_overwrites
                )

        awaitables = []
        for user in team1_users:
            awaitables.append(user.move_to(team1_channel))
        for user in team2_users:
            awaitables.append(user.move_to(team2_channel))
        await asyncio.gather(*awaitables, return_exceptions=True)

        return match_catg, team1_channel, team2_channel

    async def finalize_match(self, match_model: MatchModel, guild_model: GuildModel):
        """"""
        match_players = await db.get_match_users(match_model.id, match_model.guild)
        move_aws = [user.move_to(guild_model.prematch_channel) for user in match_players]
        delete_aws = [
            match_model.team1_channel.delete(),
            match_model.team2_channel.delete(),
            match_model.category.delete(),
            db.delete_match(match_model.id)
        ]
        await asyncio.gather(*move_aws, return_exceptions=True)
        await asyncio.gather(*delete_aws, return_exceptions=True)

    async def update_match_stats(self, match_model: MatchModel):
        """"""
        match_stats = None
        mapstats = []
        game_server = None
        message = None
        season = None
        guild_model = await db.get_guild_by_id(match_model.guild.id, self.bot)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
        except Exception as e:
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
        
        if match_stats.season_id:
            try:
                season = await api.get_season(match_stats.season_id)
            except Exception as e:
                pass

        if message:
            embed = self.embed_match_info(match_stats, game_server, mapstats, season)
            try:
                await message.edit(embed=embed)
            except Exception as e:
                pass

        if not match_stats.end_time and not match_stats.cancelled and not match_stats.forfeit:
            return

        try:
            await message.delete()
        except Exception as e:
            pass

        if mapstats and not match_stats.cancelled:
            try:
                embed = self.embed_match_info(match_stats, mapstats=mapstats, season=season)
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
            if guild_matches:
                live_match = True
                aws = [self.update_match_stats(m) for m in guild_matches]
                results = await asyncio.gather(*aws, return_exceptions=True)
                for e in results:
                    if isinstance(e, Exception):
                        self.bot.log_exception(
                            f'Uncaught exception when handling cogs.match.update_match_stats():', e)

        if not live_match:
            self.check_live_matches.cancel()


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
