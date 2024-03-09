# match.py

from discord.ext import commands
from discord import Embed, Member, Message, Guild, PermissionOverwrite, app_commands, Interaction
from typing import List

from random import choice, shuffle
import asyncio

from bot.helpers.api import Match
from bot.helpers.utils import generate_api_key, generate_scoreboard_img, set_scoreboard_image
from bot.helpers.models import GuildModel, MatchModel
from bot.bot import G5Bot
from bot.helpers.errors import APIError, CustomError
from bot.resources import Config
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

        guild_model = await self.bot.db.get_guild_by_id(interaction.guild.id)
        match_model = await self.bot.db.get_match_by_id(match_id)
        if not match_model:
            raise CustomError("Invalid match ID.")
        
        try:
            await self.bot.api.cancel_match(match_id)
        except:
            pass

        try:
            await self.bot.api.stop_game_server(match_model.game_server_id)
        except:
            pass
        
        match_api = await self.bot.api.get_match(match_id)
        await self.finalize_match(match_model, match_api, guild_model)

        embed = Embed(description=f"Match #{match_id} cancelled successfully.")
        await interaction.followup.send(embed=embed)

        try:
            match_msg = await match_model.text_channel.fetch_message(match_model.message_id)
            await match_msg.delete()
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
    
    async def autobalance_teams(self, users: List[Member]):
        """"""
        players_stats = await self.bot.db.get_players(users)
        players_stats.sort(key=lambda x: x.elo)

        # Balance teams
        team_size = len(players_stats) // 2
        team1_stats = [players_stats.pop()]
        team2_stats = [players_stats.pop()]

        while players_stats:
            if len(team1_stats) >= team_size:
                team2_stats.append(players_stats.pop())
            elif len(team2_stats) >= team_size:
                team1_stats.append(players_stats.pop())
            elif sum(p.elo for p in team1_stats) < sum(p.elo for p in team2_stats):
                team1_stats.append(players_stats.pop())
            else:
                team2_stats.append(players_stats.pop())

        team1_users = [player_model.discord for player_model in team1_stats]
        team2_users = [player_model.discord for player_model in team2_stats]
        return team1_users, team2_users

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
        game_server=None,
    ):
        """"""
        title = f"**{match_stats.team1_name}**  [ {match_stats.team1_score} : {match_stats.team2_score} ]  **{match_stats.team2_name}**"
        description = ''

        if game_server:
            description += f'📌 **Server:** `connect {game_server.ip}:{game_server.port}`\n' \
                           f'⚙️ **Game mode:** {game_server.game_mode}\n'

        description += f'🗺️ **Map:** {match_stats.map_name}\n\n'
        embed = Embed(title=title, description=description)

        author_name = f"🟢 Match #{match_stats.id}"
        embed.set_author(name=author_name)

        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.set_footer(
            text= "🔸You'll be put on a random team when joining the server.\n" \
                  "🔸Once the match starts you'll be moved to your correct team.\n" \
                 f"🔸Match will be cancelled if any player doesn't join the server within {match_stats.connect_time} seconds.\n")

        return embed

    async def start_match(
        self,
        guild: Guild,
        message: Message,
        queue_users: List[Member]=[], 
        team_method: str='captains',
        map_method: str='veto',
        captain_method: str='random',
        game_mode: str='competitive',
        connect_time: int=300,
        location: str=None
    ):
        """"""
        await asyncio.sleep(3)
        try:
            if team_method == 'captains' and len(queue_users) >= 4:
                team1_users, team2_users = await self.pick_teams(message, queue_users, captain_method)
            elif team_method == 'autobalance' and len(queue_users) >= 4:
                team1_users, team2_users = await self.autobalance_teams(queue_users)
            else:
                team1_users, team2_users = self.randomize_teams(queue_users)
            
            team1_players_model = await self.bot.db.get_players(team1_users)
            team2_players_model = await self.bot.db.get_players(team2_users)
            team1_captain = team1_users[0]
            team2_captain = team2_users[0]
            team1_name = team1_captain.display_name
            team2_name = team2_captain.display_name

            match_players = [ {
                'steam_id_64': str(player.steam_id),
                'team': 'team1' if player in team1_players_model else 'team2',
                'nickname_override': player.discord.display_name[:32]
            } for player in team1_players_model + team2_players_model]

            mpool = list(Config.maps.keys())
            if map_method == 'veto':
                veto_view = VetoView(message, mpool, team1_captain, team2_captain)
                await message.edit(embed=veto_view.embed_veto(), view=veto_view)
                await veto_view.wait()
                map_name = veto_view.maps_left[0]
            else:
                map_name = choice(mpool)

            await message.edit(embed=Embed(description='Searching for available game servers...'), view=None)
            await asyncio.sleep(2)

            game_server = await self.find_game_server()

            await message.edit(embed=Embed(description='Setting up match on game server...'), view=None)
            await asyncio.sleep(2)

            spectators = await self.bot.db.get_spectators(guild)
            for spec in spectators:
                if spec.discord not in team1_users and spec.discord not in team2_users:
                    match_players.append({'steam_id_64': spec.steam_id, 'team': 'spectator'})

            await self.bot.api.update_game_server(
                game_server.id,
                len(match_players),
                game_mode=game_mode,
                location=location)

            api_key = generate_api_key()
            api_match = await self.bot.api.create_match(
                game_server.id,
                map_name,
                team1_name,
                team2_name,
                match_players,
                connect_time,
                api_key
            )

            await message.edit(embed=Embed(description='Setting up teams channels...'), view=None)
            category, team1_channel, team2_channel = await self.create_match_channels(
                api_match.id,
                team1_users,
                team2_users,
                guild
            )

            await self.bot.db.insert_match({
                'id': api_match.id,
                'game_server_id': game_server.id,
                'guild': guild.id,
                'channel': message.channel.id,
                'message': message.id,
                'category': category.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id,
                'team1_name': team1_name,
                'team2_name': team2_name,
                'map_name': map_name,
                'api_key': api_key,
                'connect_time': api_match.connect_time
            })

            players_stats = []
            for u in team1_players_model + team2_players_model:
                players_stats.append({'match_id': api_match.id,
                                      'steam_id': u.steam_id,
                                      'user_id': u.discord.id,
                                      'team': 'team1' if u.discord in team1_users else 'team2'})
            await self.bot.db.insert_players_stats(players_stats)

            embed = self.embed_match_info(api_match, game_server)

        except APIError as e:
            description = e.message
        except asyncio.TimeoutError:
            description = 'Setup took too long!'
        except ValueError as e:
            description = e
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)
            description = 'Something went wrong! See logs for details'
        else:
            try:
                team1_stats = {
                    player_model: next(player_stat for player_stat in api_match.players if player_model.steam_id == player_stat.steam_id)
                    for player_model in team1_players_model
                }
                team2_stats = {
                    player_model: next(player_stat for player_stat in api_match.players if player_model.steam_id == player_stat.steam_id)
                    for player_model in team2_players_model
                }
                file = generate_scoreboard_img(api_match, team1_stats, team2_stats)
                set_scoreboard_image(embed)
                await message.edit(embed=embed, view=None, attachments=[file])
            except Exception as e:
                self.bot.logger.error(e, exc_info=1)

            return True

        embed = Embed(title="Match Setup Failed",
                      description=description, color=0xE02B2B)
        try:
            await message.edit(embed=embed, view=None)
        except:
            pass

    async def find_game_server(self):
        """"""
        game_servers = await self.bot.api.get_game_servers()

        for game_server in game_servers:            
            if not game_server.match_id:
                return game_server

        raise ValueError("No game server available at the moment.")

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
        team1_overwrites[guild.self_role] = PermissionOverwrite(connect=True)
        team1_overwrites[guild.default_role] = PermissionOverwrite(connect=False)
        team2_overwrites = {u: PermissionOverwrite(connect=True) for u in team2_users}
        team2_overwrites[guild.self_role] = PermissionOverwrite(connect=True)
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

    async def finalize_match(self, match_model: MatchModel, match_api: Match, guild_model: GuildModel):
        """"""
        try:
            move_aws = [user.move_to(guild_model.waiting_channel)
                        for user in match_model.team1_channel.members + match_model.team2_channel.members]
            await asyncio.gather(*move_aws, return_exceptions=True)
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)
        
        team_channels = [
            match_model.team2_channel,
            match_model.team1_channel,
            match_model.category
        ]

        for channel in team_channels:
            try:
                await channel.delete()
            except Exception as e:
                self.bot.logger.error(e, exc_info=1)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
            await message.delete()
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)
        
        await self.bot.db.update_match(match_api)


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
