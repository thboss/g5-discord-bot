# db_manager.py

import asyncpg
import logging
from typing import List, Literal, Union, Optional

import discord

from bot.resources import Config
from bot.helpers.api import MatchPlayer, Match
from bot.helpers.models.playerstats import PlayerStatsModel
from bot.helpers.models import LobbyModel, MatchModel, GuildModel, PlayerModel


class DBManager:
    """ Manages the connection to the PostgreSQL database. """

    def __init__(self, bot):
        self.db_pool = None
        self.bot = bot
        self.logger = logging.getLogger('DB')

    async def connect(self) -> None:
        """"""
        self.logger.info("Creating database connection pool.")
        db_connect_url = f'postgresql://{Config.POSTGRESQL_USER}:{Config.POSTGRESQL_PASSWORD}@{Config.POSTGRESQL_HOST}:{Config.POSTGRESQL_PORT}/{Config.POSTGRESQL_DB}'
        self.db_pool = await asyncpg.create_pool(db_connect_url)

    async def close(self) -> None:
        """"""
        self.logger.info("Closing database connection pool.")
        await self.db_pool.close()

    async def query(self, sql, *args) -> List[dict]:
        """"""
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                prepared_stmt = await connection.prepare(sql)
                result = await prepared_stmt.fetch(*args)
                return [dict(row.items()) for row in result]

    async def sync_guilds(self, guild_ids: List[int]) -> None:
        """"""
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    'CREATE TEMPORARY TABLE temp_guilds (id BIGINT) ON COMMIT DROP;'
                )
                await connection.copy_records_to_table(
                    'temp_guilds', records=[(guild_id,) for guild_id in guild_ids]
                )
                await connection.execute(
                    'INSERT INTO guilds (id) SELECT id FROM temp_guilds '
                    'ON CONFLICT (id) DO NOTHING;'
                )
                await connection.execute(
                    'DELETE FROM guilds WHERE id NOT IN (SELECT id FROM temp_guilds);'
                )

    async def get_match_by_id(self, match_id: str) -> Optional["MatchModel"]:
        """"""
        sql = "SELECT * FROM matches\n" \
            f"    WHERE id = $1;"
        data = await self.query(sql, match_id)
        if data:
            guild = self.bot.get_guild(data[0]['guild'])
            if guild:
                return MatchModel.from_dict(data[0], guild)

    async def get_match_by_api_key(self, api_key: str) -> Optional["MatchModel"]:
        """"""
        sql = "SELECT * FROM matches\n" \
            f"    WHERE api_key = $1;"
        data = await self.query(sql, api_key)
        if data:
            guild = self.bot.get_guild(data[0]['guild'])
            if guild:
                return MatchModel.from_dict(data[0], guild)

    async def get_guild_matches(self, guild: discord.Guild) -> List["MatchModel"]:
        """"""
        sql = "SELECT * FROM matches WHERE guild = $1;"
        matches_data = await self.query(sql, guild.id)
        return [MatchModel.from_dict(data, guild) for data in matches_data]

    async def get_user_match(self, user_id: int, guild: discord.Guild) -> Optional["MatchModel"]:
        """"""
        sql = "SELECT * FROM matches m\n" \
            "JOIN player_stats ps\n" \
            "    ON ps.match_id = m.id AND ps.user_id = $1\n" \
            "WHERE m.guild=$2 AND m.finished=false;"
        data = await self.query(sql, user_id, guild.id)
        if data:
            return MatchModel.from_dict(data[0], guild)

    async def insert_match(self, match_data: dict) -> None:
        """"""
        cols = ", ".join(col for col in match_data)
        vals = ", ".join(f"'{val}'" if type(val) is
                         str else str(val) for val in match_data.values())
        sql = f"INSERT INTO matches ({cols})\n" \
            f"    VALUES({vals});"

        await self.query(sql)

    async def update_match(self, match_stats: Match) -> None:
        """"""
        dict_stats = match_stats.to_dict
        dict_stats.pop('players')
        dict_stats = {key: f"'{value}'" if isinstance(value, str) else value for key, value in dict_stats.items()}
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in dict_stats.items()
        )
        sql = f"UPDATE matches SET {col_vals} WHERE id = $1;"
        await self.query(sql, match_stats.id)

    async def delete_match(self, match_id: str) -> None:
        """"""
        sql = f"DELETE FROM matches WHERE id = $1;"
        await self.query(sql, match_id)

    async def get_players_stats(self, match_id: str, team=None) -> List[PlayerStatsModel]:
        """"""
        sql = "SELECT user_id FROM player_stats\n" \
            f"    WHERE match_id = $1;"
        if team:
            sql = sql.replace(";", " AND team=$2")

        query = await self.query(sql, match_id, team)
        return [PlayerStatsModel.from_dict(data) for data in query]

    async def get_player_by_discord_id(self, user_id: int) -> Optional[PlayerModel]:
        """"""
        sql = "SELECT * FROM users\n" \
            f"    WHERE id = $1;"
        data = await self.query(sql, user_id)
        if data:
            user = self.bot.get_user(user_id)
            return PlayerModel.from_dict(data[0], user)

    async def get_player_by_steam_id(self, steam_id: int) -> Optional[PlayerModel]:
        """"""
        sql = "SELECT * FROM users\n" \
            f"    WHERE steam_id = $1;"
        data = await self.query(sql, steam_id)
        if data:
            user = self.bot.get_user(data[0]['id'])
            return PlayerModel.from_dict(data[0], user)

    async def get_players(self, users: List[discord.Member]) -> List[PlayerModel]:
        """"""
        users_ids = [u.id for u in users]
        sql = "SELECT * FROM users\n" \
            "    WHERE id = ANY($1::BIGINT[]) AND steam_id IS NOT NULL;"
        users_data = await self.query(sql, users_ids)
        db_user_ids = [u['id'] for u in users_data]
        filtered_users = list(filter(lambda x: x.id in db_user_ids, users))
        return_obj = []
        for user in filtered_users:
            for data in users_data:
                if user.id == data['id']:
                    return_obj.append(PlayerModel.from_dict(data, user))
        return return_obj

    async def insert_player(self, user_id: int, steam_id: int) -> None:
        """"""
        sql = f"INSERT INTO users (id, steam_id)\n" \
            f"    VALUES($1, $2);"
        await self.query(sql, user_id, steam_id)

    async def update_player(self, user_id: int, steam_id: int) -> None:
        """"""
        sql = 'UPDATE users SET steam_id = $1 WHERE id = $2;'
        await self.query(sql, steam_id, user_id)

    async def delete_player(self, user_id: int) -> None:
        """"""
        sql = "DELETE FROM users WHERE id = $1"
        await self.query(sql, user_id)

    async def get_lobby_by_id(self, lobby_id: int) -> Union["LobbyModel", None]:
        """"""
        sql = "SELECT * FROM lobbies WHERE id = $1;"
        data = await self.query(sql, lobby_id)
        if data:
            guild = self.bot.get_guild(data[0]['guild'])
            if guild:
                return LobbyModel.from_dict(data[0], guild)

    async def get_lobby_by_voice_channel(self, channel: discord.VoiceChannel) -> Union["LobbyModel", None]:
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE lobby_channel = $1;"
        data = await self.query(sql, channel.id)
        if data:
            return LobbyModel.from_dict(data[0], channel.guild)

    async def get_lobby_by_text_channel(self, channel: discord.TextChannel) -> Union["LobbyModel", None]:
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE queue_channel = $1;"
        data = await self.query(sql, channel.id)
        if data:
            return LobbyModel.from_dict(data[0], channel.guild)

    async def get_guild_lobbies(self, guild: discord.Guild) -> List["LobbyModel"]:
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE guild = $1;"
        lobbies = await self.query(sql, guild.id)
        return [LobbyModel.from_dict(data, guild) for data in lobbies]

    async def get_user_lobby(self, user_id: int, guild: discord.Guild) -> Union["LobbyModel", None]:
        """"""
        sql = "SELECT l.* FROM lobby_users qu\n" \
            "JOIN lobbies l\n" \
            "    ON qu.lobby_id = l.id AND l.guild = $1\n" \
            "WHERE qu.user_id = $2;"
        data = await self.query(sql, guild.id, user_id)
        if data:
            return LobbyModel.from_dict(data[0], guild)

    async def insert_lobby(self, data: dict) -> int:
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(f"'{val}'" if type(val) is
                         str else str(val) for val in data.values())
        sql = f"INSERT INTO lobbies ({cols})\n" \
            f"    VALUES({vals})\n" \
            "RETURNING id;"

        lobby = await self.query(sql)
        return list(map(lambda r: r['id'], lobby))[0]

    async def update_lobby(self, lobby_id: int, data: dict) -> None:
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = "UPDATE lobbies\n" \
            f"    SET {col_vals}\n" \
            f"    WHERE id = $1;"
        await self.query(sql, lobby_id)

    async def delete_lobby(self, lobby_id: int) -> None:
        """"""
        sql = f"DELETE FROM lobbies WHERE id = $1;"
        await self.query(sql, lobby_id)

    async def get_lobby_users(self, lobby_id: int, guild) -> List[discord.Member]:
        """"""
        sql = "SELECT user_id FROM lobby_users\n" \
            f"    WHERE lobby_id = $1;"
        query = await self.query(sql, lobby_id)
        users_ids = list(map(lambda r: r['user_id'], query))
        lobby_users = []
        for uid in users_ids:
            user = guild.get_member(uid)
            if user:
                lobby_users.append(user)
        return lobby_users

    async def insert_lobby_user(self, lobby_id: int, user: discord.Member) -> None:
        """"""
        sql = "INSERT INTO lobby_users (lobby_id, user_id)\n" \
            f"    VALUES($1, $2);"
        await self.query(sql, lobby_id, user.id)

    async def delete_lobby_users(self, lobby_id: int, users: List[discord.Member]) -> List[dict]:
        """"""
        sql = "DELETE FROM lobby_users\n" \
            f"    WHERE lobby_id = $1 AND user_id::BIGINT = ANY(ARRAY{[u.id for u in users]}::BIGINT[])\n" \
            "    RETURNING user_id;"
        return await self.query(sql, lobby_id)

    async def clear_lobby_users(self, lobby_id: int) -> None:
        """"""
        sql = f"DELETE FROM lobby_users WHERE lobby_id = $1;"
        await self.query(sql, lobby_id)

    async def get_lobby_maps(self, lobby_id: int) -> List[str]:
        """"""
        sql = "SELECT map_name FROM lobby_maps WHERE lobby_id = $1;"
        result = await self.query(sql, lobby_id)
        return [m['map_name'] for m in result]

    async def clear_lobby_maps(self, lobby_id: int) -> None:
        """"""
        sql = "DELETE FROM lobby_maps WHERE lobby_id = $1;"
        await self.query(sql, lobby_id)

    async def insert_lobby_maps(self, lobby_id: int, maps: List[str]) -> None:
        """"""
        values = f", ".join(f"({lobby_id}, '{m}')" for m in maps)
        sql = f"INSERT INTO lobby_maps (lobby_id, map_name) VALUES {values};"
        await self.query(sql)

    async def delete_lobby_maps(self, lobby_id: int, maps: List[str]) -> None:
        """"""
        sql = "DELETE FROM lobby_maps WHERE lobby_id = $1 AND map_name = ANY($2);"
        await self.query(sql, lobby_id, maps)

    async def update_lobby_maps(self, lobby_id: int, new_maps: List[str], existing_maps: List[str]) -> None:
        """"""
        delete_maps = list(set(existing_maps) - set(new_maps))
        insert_maps = list(set(new_maps) - set(existing_maps))

        if delete_maps:
            await self.delete_lobby_maps(lobby_id, delete_maps)

        if insert_maps:
            await self.insert_lobby_maps(lobby_id, insert_maps)

    async def get_guild_by_id(self, guild_id: int) -> Union["GuildModel", None]:
        """"""
        sql = "SELECT * FROM guilds\n" \
            f"    WHERE id =  $1;"
        data = await self.query(sql, guild_id)
        if data:
            guild = self.bot.get_guild(guild_id)
            return GuildModel.from_dict(data[0], guild)

    async def update_guild_data(self, guild_id: int, data: dict) -> None:
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = 'UPDATE guilds\n' \
            f'    SET {col_vals}\n' \
            f'    WHERE id = $1;'
        await self.query(sql, guild_id)
        
    async def get_spectators(self, guild: discord.Guild) -> List[PlayerModel]:
        """"""
        sql = "SELECT * FROM users u\n" \
              "JOIN spectators s\n" \
              "    ON s.user_id = u.id\n" \
              "WHERE s.guild_id = $1;"
        results = await self.query(sql, guild.id)
        return [PlayerModel.from_dict(row, guild.get_member(row["id"])) for row in results]
    
    async def insert_spectators(self, *users: List[discord.Member], guild: discord.Guild):
        """"""
        values = f", ".join(
            f"({guild.id}, {user.id})" for user in users)
        sql = f"INSERT INTO spectators VALUES {values};"
        await self.query(sql)
        
    async def delete_spectators(self, *users: List[discord.Member], guild: discord.Guild):
        """"""
        sql = "DELETE FROM spectators\n" \
             f"    WHERE user_id::BIGINT = ANY(ARRAY{[u.id for u in users]}::BIGINT[]) AND guild_id = $1\n" \
              "RETURNING user_id;"
        return await self.query(sql, guild.id)
    
    async def is_server_in_use(self, game_server_id: str):
        """"""
        sql = "SELECT id FROM matches WHERE game_server_id = $1 AND finished=false;"
        return await self.query(sql, game_server_id)
    
    async def get_player_stats(self, user_id: int, match_id: str=None):
        """"""
        sql = "SELECT * FROM player_stats WHERE user_id = $1;"
        if match_id:
            sql = sql.replace(";", " AND match_id = $2;")

        return await self.query(sql, user_id, match_id)
    
    async def insert_players_stats(self, players_stats: List[dict]):
        """"""
        values =",\n".join(f"('{ps['match_id']}', {ps['steam_id']}, {ps['user_id']}, '{ps['team']}')"
                           for ps in players_stats)
        sql = f"INSERT INTO player_stats (match_id, steam_id, user_id, team) VALUES {values};"
        await self.query(sql)
    
    async def update_player_stats(self, user_id: int, stats: MatchPlayer):
        """"""
        dict_stats = stats.to_dict
        dict_stats.pop('match_id')
        dict_stats.pop('steam_id')
        dict_stats.pop('team')
        dict_stats = {key: f"'{value}'" if isinstance(value, str) else value for key, value in dict_stats.items()}
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in dict_stats.items()
        )

        sql = f'UPDATE player_stats SET {col_vals} WHERE user_id = $1 AND match_id = $2;'
        await self.query(sql, user_id, stats.match_id)

    async def delete_player_stats(self, user_id: int):
        """"""
        sql = f'DELETE FROM player_stats WHERE user_id = $1;'
        await self.query(sql, user_id)
