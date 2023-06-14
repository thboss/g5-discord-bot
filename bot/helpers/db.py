# db_manager.py

import asyncpg
import logging
import os
from typing import List, Union, Optional

import discord
from discord.ext import commands

from bot.helpers.config_reader import Config
from .models import GuildModel, LobbyModel, MapModel, UserModel, MatchModel


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

    async def get_lobby_maps(self, lobby_id: int, guild: discord.Guild) -> List[MapModel]:
        """"""
        sql = "SELECT gm.*, lm.lobby_id\n" \
            "FROM lobby_maps lm\n" \
            "JOIN guild_maps gm\n" \
            "   ON lm.emoji_id = gm.emoji_id\n" \
            "WHERE lobby_id = $1;"
        maps_data = await self.query(sql, lobby_id)
        maps = [MapModel.from_dict(data, guild) for data in maps_data]
        return [m for m in maps if m.emoji]

    async def clear_lobby_maps(self, lobby_id: int) -> None:
        """"""
        sql = "DELETE FROM lobby_maps WHERE lobby_id = $1;"
        await self.query(sql, lobby_id)

    async def insert_lobby_maps(self, lobby_id: int, maps: List[MapModel]) -> None:
        """"""
        emojis = [m.emoji for m in maps]
        emoji_ids = [e.id for e in emojis]
        values = f", ".join(
            f"({lobby_id}, {emoji_id})" for emoji_id in emoji_ids)
        sql = f"INSERT INTO lobby_maps VALUES {values};"
        await self.query(sql)

    async def update_lobby_maps(self, lobby_id: int, new_maps: List[MapModel], existing_maps: List[MapModel]) -> None:
        """"""
        existing_emojis = [m.emoji for m in existing_maps]
        new_emojis = [m.emoji for m in new_maps]
        existing_emoji_ids = [emoji.id for emoji in existing_emojis]
        new_emoji_ids = [emoji.id for emoji in new_emojis]
        delete_emoji_ids = list(set(existing_emoji_ids) - set(new_emoji_ids))
        insert_emoji_ids = list(set(new_emoji_ids) - set(existing_emoji_ids))

        if delete_emoji_ids:
            delete_sql = "DELETE FROM lobby_maps WHERE lobby_id = $1 AND emoji_id = ANY($2);"
            await self.query(delete_sql, lobby_id, delete_emoji_ids)

        if insert_emoji_ids:
            values = ", ".join(
                f"({lobby_id}, {emoji_id})" for emoji_id in insert_emoji_ids)
            insert_sql = f"INSERT INTO lobby_maps VALUES {values};"
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
        guild_maps = [MapModel.from_dict(map_data, guild)
                      for map_data in maps_data]
        exist_maps = [m for m in guild_maps if m.emoji]

        if len(guild_maps) != len(exist_maps):
            exist_emojis_ids = ','.join([f'{m.emoji.id}' for m in exist_maps])
            sql = f"DELETE FROM guild_maps\n" \
                f"    WHERE guild_id = $1 AND emoji_id NOT IN ({exist_emojis_ids});"
            await self.query(sql, guild.id)

        return exist_maps

    async def insert_guild_maps(self, guild: discord.Guild, maps: List[MapModel]) -> None:
        """"""
        values = f", ".join(
            f"('{m.display_name}', '{m.dev_name}', {guild.id}, {m.emoji.id})" for m in maps)
        sql = "INSERT INTO guild_maps (display_name, dev_name, guild_id, emoji_id) \n" \
            f"VALUES {values};"
        await self.query(sql)

    async def delete_guild_maps(self, guild: discord.Guild, maps: List[MapModel]):
        """"""
        maps_str = ','.join([f"'{m.dev_name}'" for m in maps])
        sql = f"DELETE FROM guild_maps WHERE dev_name IN ({maps_str}) AND guild_id = $1;"
        await self.query(sql, guild.id)

    async def create_custom_guild_map(self, guild: discord.Guild, display_name: str, emoji: discord.Emoji) -> bool:
        """"""
        exist_maps = await self.get_guild_maps(guild)
        new_maps = [MapModel(
            display_name,
            emoji.name,
            guild,
            emoji,
            f'<:{emoji.name}:{emoji.id}>'
        )]

        new_maps = [m for m in new_maps if m not in exist_maps]
        if new_maps:
            await self.delete_guild_maps(guild, new_maps)
            await self.insert_guild_maps(guild, new_maps)
            return True
        return False

    async def create_default_guild_maps(self, guild: discord.Guild) -> None:
        """ Upload custom map emojis to guilds. """
        icons_dic = 'assets/maps/icons/'
        icons = os.listdir(icons_dic)
        guild_emojis_str = [e.name for e in guild.emojis]
        exist_maps = await self.get_guild_maps(guild)
        exist_maps_emojis = [m.emoji for m in exist_maps]
        new_maps = []

        for icon in icons:
            if icon.endswith('.png') and os.stat(icons_dic + icon).st_size < 256000:
                display_name = icon.split('-')[0]
                dev_name = icon.split('-')[1].split('.')[0]

                if dev_name in guild_emojis_str:
                    emoji = discord.utils.get(guild.emojis, name=dev_name)
                else:
                    with open(icons_dic + icon, 'rb') as image:
                        try:
                            emoji = await guild.create_custom_emoji(name=dev_name, image=image.read())
                            self.logger.info(
                                f'Emoji "{emoji.name}" has been successfully created in server "{guild.name}"')
                        except discord.Forbidden:
                            msg = 'Setup Failed: Bot does not have permission to create custom emojis in this server!'
                            raise commands.CommandInvokeError(msg)
                        except discord.HTTPException as e:
                            msg = f'Setup Failed: {e.text}'
                            raise commands.CommandInvokeError(msg)
                        except Exception as e:
                            msg = f'Exception {e} occurred on creating custom emoji for icon "{dev_name}"'
                            raise commands.CommandInvokeError(msg)

                if emoji not in exist_maps_emojis:
                    new_maps.append(MapModel(
                        display_name,
                        dev_name,
                        guild,
                        emoji,
                        f'<:{dev_name}:{emoji.id}>'
                    ))

        if new_maps:
            await self.delete_guild_maps(guild, new_maps)
            await self.insert_guild_maps(guild, new_maps)


db = DBManager()
