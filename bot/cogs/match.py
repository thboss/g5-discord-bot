# match.py

from discord.ext import commands, tasks
from discord import Embed, NotFound, app_commands, Member, Message, Interaction
from typing import Literal, List

from random import sample, shuffle
from datetime import datetime
import traceback
import asyncio

from bot.helpers.api import api, Match, MapStat, Server
from bot.helpers.db import db
from bot.helpers.models import GuildModel, LobbyModel, MatchModel, MapModel
from bot.bot import G5Bot
from bot.helpers.errors import CustomError, APIError
from bot.helpers.config_reader import Config
from bot.messages import VetoView, PickTeamsView


class MatchCog(commands.Cog, name="Match"):
    """"""

    def __init__(self, bot: G5Bot):
        self.bot = bot

    @app_commands.command(name="cancel-match", description="Cancel a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def cancel_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.cancel_match(match_id)
        embed = Embed(description=f"Match #{match_id} successfully canceled.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="restart-match", description="Restart a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.restart_match(match_id)
        embed = Embed(description=f"Match #{match_id} successfully restarted.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause-match", description="Pause a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def pause_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.pause_match(match_id)
        embed = Embed(description=f"Match #{match_id} successfully paused.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unpause-match", description="Unpause a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def unpause_match(self, interaction: Interaction, match_id: int):
        """"""
        await interaction.response.defer()
        await api.unpause_match(match_id)
        embed = Embed(description=f"Match #{match_id} successfully unpaused.")
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
            team_name = "Spectator"

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

    async def draft_teams(self, message: Message, users: List[Member], lobby_model: LobbyModel):
        """"""
        menu = PickTeamsView(message, users)
        teams = await menu.get_teams(lobby_model.captain_method)
        return teams[0], teams[1]

    def randomize_teams(self, users: List[Member]):
        """"""
        temp_users = users.copy()
        shuffle(temp_users)
        team_size = len(temp_users) // 2
        team1_users = temp_users[:team_size]
        team2_users = temp_users[team_size:]
        return team1_users, team2_users

    async def veto_map(self, message: Message, series: str, map_pool: List[MapModel], captain1: Member, captain2: Member):
        veto_view = VetoView(message, map_pool[:7], series, [
                             captain1, captain2])
        return await veto_view.start_veto()

    def random_map(self, mpool: List[MapModel], series: Literal["bo1", "bo2", "bo3"]):
        """"""
        return sample(mpool, int(series[2]))

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

    async def start_match(self, users: List[Member], lobby_model: LobbyModel, guild_model: GuildModel, message: Message):
        """"""
        team1_id = None
        team2_id = None
        team1_name = None
        team2_name = None
        team1_users = None
        team2_users = None
        try:
            if lobby_model.team_method == 'captains' and len(users) > 3:
                team1_users, team2_users = await self.draft_teams(message, users, lobby_model)
            elif lobby_model.team_method == 'autobalance' and len(users) > 3:
                team1_users, team2_users = await self.autobalance_teams(users)
            else:  # team_method is random
                team1_users, team2_users = self.randomize_teams(users)

            team1_name = team1_users[0].display_name
            team2_name = team2_users[0].display_name
            team1_id = await api.create_team(team1_name, team1_users)
            team2_id = await api.create_team(team2_name, team2_users)

            mpool = await db.get_lobby_maps(lobby_model.id)
            if lobby_model.map_method == 'veto':
                maps_list = await self.veto_map(message, lobby_model.series, mpool, team1_users[0], team2_users[0])
            else:
                maps_list = self.random_map(mpool, lobby_model.series)

            match_server = await self.find_match_server(lobby_model.region)

            str_maps = ' '.join(m.dev_name for m in maps_list)
            match_id = await api.create_match(
                match_server.id,
                team1_id,
                team2_id,
                str_maps,
                len(team1_users + team2_users),
                lobby_model.game_mode
            )

        except asyncio.TimeoutError:
            description = 'Setup took too long!'
        except NotFound:
            description = 'Setup message removed!'
        except APIError as e:
            description = e.message
        except ValueError as e:
            description = e
        except Exception as e:
            exc_lines = traceback.format_exception(
                type(e), e, e.__traceback__)
            exc = ''.join(exc_lines)
            self.bot.logger.error(exc)
            description = 'Something went wrong! See logs for details'
        else:
            category, team1_channel, team2_channel = await self.create_match_channels(
                match_id,
                team1_name,
                team2_name,
                team1_users,
                team2_users,
                guild_model
            )

            await db.insert_match({
                'id': match_id,
                'team1_id': team1_id,
                'team2_id': team2_id,
                'lobby': lobby_model.id,
                'guild': guild_model.guild.id,
                'message': message.id,
                'category': category.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id
            })

            match_stats = await api.get_match(match_id)
            await db.insert_match_users(match_id, team1_users + team2_users)
            embed = self.embed_match_info(match_stats, match_server)

            try:
                await message.edit(embed=embed)
            except NotFound:
                try:
                    await lobby_model.text_channel.send(embed=embed)
                except Exception as e:
                    self.bot.logger.info(str(e))

            if not self.check_live_matches.is_running():
                self.check_live_matches.start()

            return True

        # Delete the created teams from api if setup didn't complete
        if team1_id:
            try:
                await api.delete_team(team1_id)
            except Exception as e:
                self.bot.logger.warning(str(e))

        if team2_id:
            try:
                await api.delete_team(team2_id)
            except Exception as e:
                self.bot.logger.warning(str(e))

        embed = Embed(title="Match Setup Failed",
                      description=description, color=0xE02B2B)
        try:
            await message.edit(embed=embed, view=None, delete_after=30)
        except Exception as e:
            pass

    async def find_match_server(self, region):
        """"""
        try:
            servers = await api.get_servers()
        except Exception as e:
            self.bot.logger.warning(str(e))
            raise Exception(str(e))

        for server in servers:
            if server.in_use:
                continue

            if region and server.flag != region:
                continue

            try:
                return await api.is_server_available(server.id)
            except Exception as e:
                self.bot.logger.warning(str(e))
                continue

        raise ValueError("No game server available.")

    async def create_match_channels(
        self,
        match_id: int,
        team1_name: str,
        team2_name: str,
        team1_users: List[Member],
        team2_users: List[Member],
        guild_model: GuildModel
    ):
        """"""
        match_catg = await guild_model.guild.create_category_channel(f"Match #{match_id}")

        team1_channel = await guild_model.guild.create_voice_channel(
            name=f"Team {team1_name}",
            category=match_catg
        )

        team2_channel = await guild_model.guild.create_voice_channel(
            name=f"Team {team2_name}",
            category=match_catg
        )

        await team1_channel.set_permissions(guild_model.guild.self_role, connect=True)
        await team2_channel.set_permissions(guild_model.guild.self_role, connect=True)
        await team1_channel.set_permissions(guild_model.guild.default_role, connect=False, read_messages=True)
        await team2_channel.set_permissions(guild_model.guild.default_role, connect=False, read_messages=True)

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
        lobby_model = await db.get_lobby_by_id(match_model.lobby_id, self.bot)

        if not lobby_model:
            await self.finalize_match(match_model, guild_model)
            return

        try:
            message = await lobby_model.text_channel.fetch_message(match_model.message_id)
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
