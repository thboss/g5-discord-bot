# match.py

from discord.ext import commands, tasks
from discord.errors import HTTPException
from discord import Embed, Member, Message, Guild, PermissionOverwrite, app_commands, Interaction
from typing import List

from random import choice, shuffle
import asyncio

from bot.helpers.api import api, Match
from bot.helpers.db import db
from bot.helpers.models import GuildModel, MatchModel, UserModel
from bot.bot import G5Bot
from bot.helpers.errors import APIError, CustomError
from bot.views import VetoView, PickTeamsView


class MatchCog(commands.Cog, name="Match"):
    """"""

    def __init__(self, bot: G5Bot):
        self.bot = bot

    @app_commands.command(name="cancel-match", description="Cancel a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def cancel_match(self, interaction: Interaction, match_id: str):
        """"""
        await interaction.response.defer()

        guild_model = await db.get_guild_by_id(interaction.guild.id, self.bot)
        match_model = await db.get_match_by_id(match_id, self.bot)
        match_players = await db.get_match_users(match_id, match_model.guild)
        if not match_model:
            raise CustomError("Invalid match ID.")
        
        await self.finalize_match(match_model, guild_model)

        embed = Embed(description=f"Match #{match_id} cancelled successfully.")
        await interaction.followup.send(embed=embed)

        try:
            match_msg = await match_model.text_channel.fetch_message(match_model.message_id)
            await match_msg.delete()
        except Exception as e:
            pass

        api_match = await api.get_match(match_id)
        api_match.finished = True
        try:
            embed = self.embed_match_info(api_match)
            match_players = await db.get_users(match_players)
            self.add_teams_fields(embed, api_match, match_players)
            await guild_model.results_channel.send(embed=embed)
        except:
            pass

        try:
            await api.stop_game_server(match_model.game_server_id)
            await api.start_game_server(match_model.game_server_id)
        except:
            pass

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
    
    def add_teams_fields(self, embed: Embed, match_stats: Match, match_players: List[UserModel]):
        """"""
        team1_steam_ids = [player.steam_id for player in match_stats.team1_players]
        team2_steam_ids = [player.steam_id for player in match_stats.team2_players]
        team1_users = list(filter(lambda u: u.steam in team1_steam_ids, match_players))
        team2_users = list(filter(lambda u: u.steam in team2_steam_ids, match_players))

        embed.add_field(name="Team 1", value="\n".join(u.member.mention for u in team1_users))
        embed.add_field(name="Team 2", value="\n".join(u.member.mention for u in team2_users))

    def embed_match_info(
        self,
        match_stats: Match,
        game_server=None,
    ):
        """"""
        title = f"Team **{match_stats.team1_name}**  [ {match_stats.team1_score} : {match_stats.team2_score} ]  Team **{match_stats.team2_name}**"
        description = ''

        if game_server:
            description += f'📌 **Server:** `connect {game_server.ip}:{game_server.port}`\n' \
                           f'⚙️ **Game mode:** {game_server.game_mode}\n'

        description += f'🗺️ **Map:** {match_stats.map}\n\n'
        embed = Embed(title=title, description=description)

        is_live = not match_stats.finished and not match_stats.cancel_reason
        author_name = f"{'🟢' if is_live else '🔴'} Match #{match_stats.id}"
        embed.set_author(name=author_name)

        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        if is_live:
            embed.set_footer(
                text= "🔸You'll be put on a random team when joining the server.\n" \
                      "🔸Warmup is deathmatch mode with all players being enemies.\n" \
                      "🔸Once the match starts you'll be moved to your correct team.\n" \
                     f"🔸Match will be cancelled if any player doesn't join the server within {match_stats.connect_time} seconds.\n")
        else:
            if match_stats.cancel_reason and "MISSING_PLAYERS" in match_stats.cancel_reason:
                embed.set_footer(text="Cancel Reason: Some players didn't join the game server.")
        return embed

    async def start_match(
        self,
        guild: Guild,
        message: Message,
        mpool: List[str],
        queue_users: List[Member]=[], 
        team_method: str='captains',
        map_method: str='veto',
        captain_method: str='random',
        game_mode: str='competitive'
    ):
        """"""
        await asyncio.sleep(3)
        try:
            if team_method == 'captains' and len(queue_users) >= 4:
                team1_users, team2_users = await self.pick_teams(message, queue_users, captain_method)
            else:
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
                veto_view = VetoView(message, mpool, team1_captain, team2_captain)
                await message.edit(embed=veto_view.embed_veto(), view=veto_view)
                await veto_view.wait()
                map_name = veto_view.maps_left[0]
            else:
                map_name = choice(mpool)

            await message.edit(embed=Embed(description='Searching for available game servers...'), view=None)
            await asyncio.sleep(2)

            game_server = await self.find_match_server()

            await message.edit(embed=Embed(description='Setting up match on game server...'), view=None)
            await asyncio.sleep(2)

            spectators = await db.get_spectators(guild)
            for spec in spectators:
                if spec.member not in team1_users and spec.member not in team2_users:
                    match_players.append({'steam_id_64': spec.steam, 'team': 'spectator'})

            api_match = await api.create_match(
                game_server.id,
                map_name,
                team1_name,
                team2_name,
                match_players
            )

            await api.update_game_mode(game_server.id, game_mode)

            await message.edit(embed=Embed(description='Setting up teams channels...'), view=None)
            category, team1_channel, team2_channel = await self.create_match_channels(
                api_match.id,
                team1_users,
                team2_users,
                guild
            )

            await db.insert_match({
                'id': api_match.id,
                'game_server_id': game_server.id,
                'guild': guild.id,
                'channel': message.channel.id,
                'message': message.id,
                'category': category.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id
            })

            await db.insert_match_users(api_match.id, team1_users + team2_users)
            embed = self.embed_match_info(api_match, game_server)
            match_players = team1_users_model + team2_users_model
            self.add_teams_fields(embed, api_match, match_players)

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
            
            if not await db.is_server_in_use(game_server.id):
                return game_server

        raise ValueError("No game server available.")

    async def create_match_channels(
        self,
        match_id: int,
        team1_users: List[Member],
        team2_users: List[Member],
        guild: Guild
    ):
        """"""
        match_catg = await guild.create_category_channel(f"Match #{match_id}")
        team1_overwrites = {u: PermissionOverwrite(connect=True) for u in team1_users}
        team1_overwrites[guild.default_role] = PermissionOverwrite(connect=False)
        team2_overwrites = {u: PermissionOverwrite(connect=True) for u in team2_users}
        team2_overwrites[guild.default_role] = PermissionOverwrite(connect=False)

        team1_channel = await guild.create_voice_channel(
            name=f"Team 1",
            category=match_catg,
            overwrites=team1_overwrites
        )
    
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
        await db.delete_match(match_model.id)

        match_players = await db.get_match_users(match_model.id, match_model.guild)
        move_aws = [user.move_to(guild_model.waiting_channel) for user in match_players]
        
        try:
            await match_model.team1_channel.delete()
            await match_model.team2_channel.delete()
            await match_model.category.delete()
        except:
            pass

        await asyncio.gather(*move_aws, return_exceptions=True)

    async def update_match_stats(self, match_model: MatchModel):
        """"""
        api_match = None
        game_server = None
        message = None
        guild_model = await db.get_guild_by_id(match_model.guild.id, self.bot)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
        except Exception as e:
            pass

        try:
            api_match = await api.get_match(match_model.id)
        except Exception as e:
            pass

        if not api_match:
            await self.finalize_match(match_model, guild_model)
            return

        try:
            game_server = await api.get_game_server(api_match.game_server_id)
        except Exception as e:
            pass

        if message:
            embed = self.embed_match_info(api_match, game_server)
            match_players = await db.get_match_users(api_match.id, match_model.guild)
            match_players = await db.get_users(match_players)
            self.add_teams_fields(embed, api_match, match_players)
            try:
                await message.edit(embed=embed)
            except Exception as e:
                pass

        if not api_match.finished and not api_match.cancel_reason:
            return

        try:
            await message.delete()
        except Exception as e:
            pass

        try:
            embed = self.embed_match_info(api_match)
            match_players = await db.get_match_users(api_match.id, match_model.guild)
            match_players = await db.get_users(match_players)
            self.add_teams_fields(embed, api_match, match_players)
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
