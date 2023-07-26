# db_manager.py

import asyncpg
import logging
from typing import List, Union, Optional

import discord

from bot.helpers.config_reader import Config
from bot.helpers.models import LobbyModel, MapModel, MatchModel, GuildModel, UserModel, TeamModel


class DBManager:
    """ Manages the connection to the PostgreSQL database. """

    def __init__(self):
        self.db_pool = None
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

    async def get_match_by_id(self, match_id: int, bot) -> Optional["MatchModel"]:
        """"""
        sql = "SELECT * FROM matches\n" \
            f"    WHERE id = $1;"
        data = await self.query(sql, match_id)
        if data:
            guild = bot.get_guild(data[0]['guild'])
            if guild:
                return MatchModel.from_dict(data[0], guild)

    async def get_guild_matches(self, guild: discord.Guild) -> List["MatchModel"]:
        """"""

        sql = "SELECT * FROM matches WHERE guild = $1;"
        matches_data = await self.query(sql, guild.id)
        return [MatchModel.from_dict(data, guild) for data in matches_data]

    async def get_user_match(self, user_id: int, guild: discord.Guild) -> Optional["MatchModel"]:
        """"""
        sql = "SELECT m.* FROM match_users mu\n" \
            "JOIN matches m\n" \
            "    ON mu.match_id = m.id AND m.guild = $1\n" \
            "WHERE mu.user_id = $2;"
        data = await self.query(sql, guild.id, user_id)
        if data:
            return MatchModel.from_dict(data[0], guild)

    async def insert_match(self, data: dict) -> None:
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO matches ({cols})\n" \
            f"    VALUES({vals});"
        await self.query(sql)

    async def insert_match_users(self, match_id: int, users: List[discord.Member]) -> None:
        """"""
        values = f", ".join(
            f"({match_id}, {user.id})" for user in users)
        sql = f"INSERT INTO match_users VALUES {values};"
        await self.query(sql)

    async def delete_match_user(self, match_id: int, user: discord.Member) -> None:
        """"""
        sql = "DELETE FROM match_users\n" \
            f"    WHERE match_id = $1 AND user_id = $2;"
        await self.query(sql, match_id, user.id)

    async def delete_match(self, match_id: int) -> None:
        """"""
        sql = f"DELETE FROM matches WHERE id = $1;"
        await self.query(sql, match_id)

    async def get_match_users(self, match_id: int, guild: discord.Guild) -> List[discord.Member]:
        """"""
        sql = "SELECT user_id FROM match_users\n" \
            f"    WHERE match_id = $1;"
        query = await self.query(sql, match_id)
        users_ids = list(map(lambda r: r['user_id'], query))
        match_users = []
        for uid in users_ids:
            user = guild.get_member(uid)
            if user:
                match_users.append(user)
        return match_users

    async def get_user_by_discord_id(self, user_id: int, bot) -> Optional["UserModel"]:
        """"""
        sql = "SELECT * FROM users\n" \
            f"    WHERE discord_id = $1;"
        data = await self.query(sql, user_id)
        if data:
            user = bot.get_user(user_id)
            return UserModel.from_dict(data[0], user)

    async def get_user_by_steam_id(self, steam_id: str, bot) -> Optional["UserModel"]:
        """"""
        sql = "SELECT * FROM users\n" \
            f"    WHERE steam_id = $1;"
        data = await self.query(sql, steam_id)
        if data:
            user = bot.get_user(data[0]['discord_id'])
            return UserModel.from_dict(data[0], user)

    async def get_users(self, users: List[discord.Member]) -> List["UserModel"]:
        """"""
        users_ids = [u.id for u in users]
        sql = "SELECT * FROM users\n" \
            "    WHERE discord_id = ANY($1::BIGINT[]) AND steam_id IS NOT NULL;"
        users_data = await self.query(sql, users_ids)
        db_user_ids = [u['discord_id'] for u in users_data]
        filtered_users = list(filter(lambda x: x.id in db_user_ids, users))
        return_obj = []
        for user in filtered_users:
            for data in users_data:
                if user.id == data['discord_id']:
                    return_obj.append(UserModel.from_dict(data, user))
        return return_obj

    async def insert_user(self, data: dict) -> None:
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO users ({cols})\n" \
            f"    VALUES({vals})"
        await self.query(sql)

    async def update_user(self, user_id: int, data: dict) -> None:
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = 'UPDATE users\n' \
            f'    SET {col_vals}\n' \
            f'    WHERE discord_id = $1;'
        await self.query(sql, user_id)

    async def delete_user(self, user_id: int) -> None:
        """"""
        sql = "DELETE FROM users WHERE discord_id = $1"
        await self.query(sql, user_id)

    async def get_lobby_by_id(self, lobby_id: int, bot) -> Union["LobbyModel", None]:
        """"""
        sql = "SELECT * FROM lobbies WHERE id = $1;"
        data = await self.query(sql, lobby_id)
        if data:
            guild = bot.get_guild(data[0]['guild'])
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
        sql = "SELECT l.* FROM queued_users qu\n" \
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

    async def update_lobby_data(self, lobby_id: int, data: dict) -> None:
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
        sql = "SELECT user_id FROM queued_users\n" \
            f"    WHERE lobby_id = $1;"
        query = await self.query(sql, lobby_id)
        users_ids = list(map(lambda r: r['user_id'], query))
        queued_users = []
        for uid in users_ids:
            user = guild.get_member(uid)
            if user:
                queued_users.append(user)
        return queued_users

    async def insert_lobby_user(self, lobby_id: int, user: discord.Member) -> None:
        """"""
        sql = "INSERT INTO queued_users (lobby_id, user_id)\n" \
            f"    VALUES($1, $2);"
        await self.query(sql, lobby_id, user.id)

    async def delete_lobby_users(self, lobby_id: int, users: List[discord.Member]) -> List[dict]:
        """"""
        sql = "DELETE FROM queued_users\n" \
            f"    WHERE lobby_id = $1 AND user_id::BIGINT = ANY(ARRAY{[u.id for u in users]}::BIGINT[])\n" \
            "    RETURNING user_id;"
        return await self.query(sql, lobby_id)

    async def clear_lobby_users(self, lobby_id: int) -> None:
        """"""
        sql = f"DELETE FROM queued_users WHERE lobby_id = $1;"
        await self.query(sql, lobby_id)

    async def get_lobby_maps(self, lobby_id: int) -> List[MapModel]:
        """"""
        sql = "SELECT gm.*\n" \
            "FROM lobby_maps lm\n" \
            "JOIN guild_maps gm\n" \
            "   ON lm.map_id = gm.map_id\n" \
            "WHERE lobby_id = $1;"
        maps_data = await self.query(sql, lobby_id)
        return [MapModel.from_dict(data) for data in maps_data]

    async def clear_lobby_maps(self, lobby_id: int) -> None:
        """"""
        sql = "DELETE FROM lobby_maps WHERE lobby_id = $1;"
        await self.query(sql, lobby_id)

    async def insert_lobby_maps(self, lobby_id: int, maps: List[MapModel]) -> None:
        """"""
        values = f", ".join(
            f"({lobby_id}, {m.map_id})" for m in maps)
        sql = f"INSERT INTO lobby_maps (lobby_id, map_id) VALUES {values};"
        await self.query(sql)

    async def update_lobby_maps(self, lobby_id: int, new_maps: List[MapModel], existing_maps: List[MapModel]) -> None:
        """"""
        existing_map_ids = [m.map_id for m in existing_maps]
        new_map_ids = [m.map_id for m in new_maps]
        delete_map_ids = list(set(existing_map_ids) - set(new_map_ids))
        insert_map_ids = list(set(new_map_ids) - set(existing_map_ids))

        if delete_map_ids:
            delete_sql = "DELETE FROM lobby_maps WHERE lobby_id = $1 AND map_id = ANY($2);"
            await self.query(delete_sql, lobby_id, delete_map_ids)

        if insert_map_ids:
            values = ", ".join(
                f"({lobby_id}, {map_id})" for map_id in insert_map_ids)
            insert_sql = f"INSERT INTO lobby_maps (lobby_id, map_id) VALUES {values};"
            await self.query(insert_sql)

    async def get_lobby_cvars(self, lobby_id: int) -> dict:
        """"""
        sql = "SELECT name, value FROM lobby_cvars WHERE lobby_id = $1;"
        query = await self.query(sql, lobby_id)
        return {r['name']: r['value'] for r in query}

    async def insert_lobby_cvar(self, lobby_id: int, key: str, value: str) -> None:
        """"""
        sql = f"INSERT INTO lobby_cvars VALUES ($1, $2, $3);"
        await self.query(sql, key, value, lobby_id)

    async def update_lobby_cvar(self, lobby_id: int, key: str, value: str) -> None:
        """"""
        sql = f"UPDATE lobby_cvars SET value = $1 WHERE name = $2 AND lobby_id = $3;"
        await self.query(sql, value, key, lobby_id)

    async def delete_lobby_cvar(self, lobby_id: int, key: str) -> None:
        """"""
        sql = f"DELETE FROM lobby_cvars WHERE name = $1 AND lobby_id = $2;"
        await self.query(sql, key, lobby_id)

    async def get_guild_by_id(self, guild_id: int, bot) -> Union["GuildModel", None]:
        """"""
        sql = "SELECT * FROM guilds\n" \
            f"    WHERE id =  $1;"
        data = await self.query(sql, guild_id)
        if data:
            guild = bot.get_guild(guild_id)
            return GuildModel.from_dict(data[0], guild)

    async def update_guild_data(self, guild_id: int, data: dict) -> None:
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = 'UPDATE guilds\n' \
            f'    SET {col_vals}\n' \
            f'    WHERE id = $1;'
        await self.query(sql, guild_id)

    async def get_guild_maps(self, guild: discord.Guild) -> List[MapModel]:
        """"""
        sql = "SELECT * FROM guild_maps\n" \
            f"    WHERE guild_id = $1;"
        maps_data = await self.query(sql, guild.id)
        return [MapModel.from_dict(map_data) for map_data in maps_data]

    async def insert_guild_maps(self, guild: discord.Guild, maps: List[MapModel]) -> None:
        """"""
        values = f", ".join(
            f"('{m.display_name}', '{m.dev_name}', {guild.id})" for m in maps)
        sql = "INSERT INTO guild_maps (display_name, dev_name, guild_id) \n" \
            f"VALUES {values};"
        await self.query(sql)

    async def delete_guild_maps(self, guild: discord.Guild, maps: List[MapModel]):
        """"""
        maps_dev_names = ','.join([f"'{m.dev_name}'" for m in maps])
        sql = f"DELETE FROM guild_maps WHERE dev_name IN ({maps_dev_names}) AND guild_id = $1;"
        await self.query(sql, guild.id)

    async def create_custom_guild_map(self, guild: discord.Guild, display_name: str, dev_name: str) -> bool:
        """"""
        existing_maps = await self.get_guild_maps(guild)
        for m in existing_maps:
            if m.dev_name == dev_name:
                return False

        await self.insert_guild_maps(guild, [MapModel(
            display_name,
            dev_name
        )])
        return True

    async def create_default_guild_maps(self, guild: discord.Guild) -> None:
        """"""
        existing_maps = await self.get_guild_maps(guild)
        default_maps_dict = {
            'de_dust2': 'Dust II',
            'de_inferno': 'Inferno',
            'de_vertigo': 'Vertigo',
            'de_overpass': 'Overpass',
            'de_mirage': 'Mirage',
            'de_nuke': 'Nuke',
            'de_train': 'Train',
            'de_ancient': 'Ancient',
            'de_cache': 'Cache',
        }
        default_maps = [MapModel(display_name, dev_name)
                        for dev_name, display_name in default_maps_dict.items()]

        existing_map_dev_names = [m.dev_name for m in existing_maps]
        new_maps = [
            m for m in default_maps if m.dev_name not in existing_map_dev_names]

        if new_maps:
            await self.insert_guild_maps(guild, new_maps)

    async def get_team_by_id(self, team_id: int, bot) -> Union["TeamModel", None]:
        """"""
        sql = "SELECT * FROM teams WHERE id = $1;"
        data = await self.query(sql, team_id)
        if data:
            guild = bot.get_guild(data[0]['guild'])
            if guild:
                return TeamModel.from_dict(data[0], guild)
            
    async def get_team_by_role(self, role: discord.Role, bot) -> Union["TeamModel", None]:
        """"""
        sql = "SELECT * FROM teams WHERE role = $1;"
        data = await self.query(sql, role.id)
        if data:
            guild = bot.get_guild(data[0]['guild'])
            if guild:
                return TeamModel.from_dict(data[0], guild)
            
    async def get_guild_teams(self, guild: discord.Guild):
        """"""
        sql = "SELECT * FROM teams WHERE guild = $1;"
        data = await self.query(sql, guild.id)
        return [TeamModel.from_dict(team_data, guild) for team_data in data]
    
    async def insert_team(self, data: dict) -> None:
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO teams ({cols})\n" \
            f"    VALUES({vals});"
        await self.query(sql)

    async def update_team(self, team_id: int, **kwargs) -> None:
        """"""
        sql = "UPDATE teams SET $2 WHERE id = $1;"
        await self.query(sql, team_id, **kwargs)

    async def insert_team_users(self, team_id: int, users: List[discord.Member]) -> None:
        """"""
        values = f", ".join(
            f"({team_id}, {user.id})" for user in users)
        sql = f"INSERT INTO team_users VALUES {values};"
        await self.query(sql)

    async def delete_team_users(self, team_id: int, users: List[discord.Member]) -> List[dict]:
        """"""
        sql = "DELETE FROM team_users\n" \
            f"    WHERE team_id = $1 AND user_id::BIGINT = ANY(ARRAY{[u.id for u in users]}::BIGINT[])\n" \
            "    RETURNING user_id;"
        return await self.query(sql, team_id)
    
    async def get_user_team(self, user_id: int, guild: discord.Guild) -> Optional[TeamModel]:
        """"""
        sql = "SELECT t.* FROM teams t\n" \
            "JOIN team_users tu\n" \
            "    ON tu.team_id = t.id AND t.guild = $1\n" \
            "WHERE tu.user_id = $2;"
        data = await self.query(sql, guild.id, user_id)
        if data:
            return TeamModel.from_dict(data[0], guild)
        
    async def get_team_users(self, team_id: int, guild: discord.Guild) -> List[discord.Member]:
        """"""
        sql = "SELECT user_id FROM team_users tu\n" \
            "JOIN teams t\n" \
            "    ON tu.team_id = t.id AND t.guild = $1\n" \
            "WHERE tu.team_id = $2;"
        data = await self.query(sql, guild.id, team_id)
        users_ids = list(map(lambda r: r['user_id'], data))
        team_users = []
        for uid in users_ids:
            user = guild.get_member(uid)
            if user:
                team_users.append(user)
        return team_users
    
    async def delete_team(self, team_id: int, guild: discord.Guild):
        """"""
        sql = "DELETE FROM teams WHERE id = $1 AND guild = $2;"
        await self.query(sql, team_id, guild.id)


db = DBManager()
