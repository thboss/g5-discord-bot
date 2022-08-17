# lobby.py

from ...resources import G5
from .map import Map


class Lobby:
    """"""

    def __init__(
        self,
        lobby_id,
        guild,
        region,
        capacity,
        series,
        category,
        queue_channel,
        lobby_channel,
        message_id,
        team_method,
        captain_method,
        season_id,
        pug,
        team1_id,
        team2_id,
        autoready
    ):
        """"""
        self.id = lobby_id
        self.guild = guild
        self.region = region
        self.capacity = capacity
        self.series = series
        self.category = category
        self.queue_channel = queue_channel
        self.lobby_channel = lobby_channel
        self.message_id = message_id
        self.team_method = team_method
        self.captain_method = captain_method
        self.season_id = season_id
        self.pug = pug
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.autoready = autoready

    @classmethod
    def from_dict(cls, lobby_data: dict):
        """"""
        guild = G5.bot.get_guild(lobby_data['guild'])
        return cls(
            lobby_data['id'],
            guild,
            lobby_data['region'],
            lobby_data['capacity'],
            lobby_data['series_type'],
            guild.get_channel(lobby_data['category']),
            guild.get_channel(lobby_data['queue_channel']),
            guild.get_channel(lobby_data['lobby_channel']),
            lobby_data['last_message'],
            lobby_data['team_method'],
            lobby_data['captain_method'],
            lobby_data['season_id'],
            lobby_data['pug'],
            lobby_data['team1_id'],
            lobby_data['team2_id'],
            lobby_data['autoready']
        )

    @staticmethod
    async def get_lobby_by_id(lobby_id: int, guild_id: int):
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE id = $1 AND guild = $2;"
        lobby_data = await G5.db.query(sql, lobby_id, guild_id)
        if lobby_data:
            return Lobby.from_dict(lobby_data[0])

    @staticmethod
    async def get_lobby_by_voice_channel(channel):
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE lobby_channel = $1;"
        lobby_data = await G5.db.query(sql, channel.id)
        if lobby_data:
            return Lobby.from_dict(lobby_data[0])

    @staticmethod
    async def get_lobby_by_text_channel(channel):
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE queue_channel = $1;"
        lobby_data = await G5.db.query(sql, channel.id)
        if lobby_data:
            return Lobby.from_dict(lobby_data[0])

    @staticmethod
    async def get_guild_lobbies(guild):
        """"""
        sql = "SELECT * FROM lobbies\n" \
              f"    WHERE guild = $1;"
        lobbies = await G5.db.query(sql, guild.id)
        return [Lobby.from_dict(lobby_data) for lobby_data in lobbies]

    @staticmethod
    async def get_user_lobby(user_id, guild_id):
        """"""
        sql = "SELECT l.* FROM queued_users qu\n" \
            "JOIN lobbies l\n" \
            "    ON qu.lobby_id = l.id AND l.guild = $1\n" \
            "WHERE qu.user_id = $2;"
        lobby_data = await G5.db.query(sql, guild_id, user_id)
        if lobby_data:
            return Lobby.from_dict(lobby_data[0])

    @staticmethod
    async def get_team_lobby(team_id):
        """"""
        sql = "SELECT * FROM lobbies\n" \
              "    WHERE team1_id = $1 OR team2_id = $2"
        query = await G5.db.query(sql, team_id, team_id)
        if query:
            return Lobby.from_dict(query[0])

    @staticmethod
    async def insert_lobby(data: dict):
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO lobbies ({cols})\n" \
              f"    VALUES({vals})\n" \
            "RETURNING id;"
        lobby = await G5.db.query(sql)
        return list(map(lambda r: r['id'], lobby))[0]

    async def update(self, data: dict):
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = "UPDATE lobbies\n" \
              f"    SET {col_vals}\n" \
              f"    WHERE id = $1;"
        await G5.db.query(sql, self.id)

    async def delete(self):
        """"""
        sql = f"DELETE FROM lobbies WHERE id = $1;"
        await G5.db.query(sql, self.id)

    async def get_users(self):
        """"""
        sql = "SELECT user_id FROM queued_users\n" \
              f"    WHERE lobby_id = $1;"
        query = await G5.db.query(sql, self.id)
        users_ids = list(map(lambda r: r['user_id'], query))
        queued_users = []
        for uid in users_ids:
            user = self.guild.get_member(uid)
            if user:
                queued_users.append(user)
            else:
                await self.delete_users([uid])
        return queued_users

    async def insert_user(self, user_id: int):
        """"""
        sql = "INSERT INTO queued_users (lobby_id, user_id)\n" \
              f"    VALUES($1, $2);"
        await G5.db.query(sql, self.id, user_id)

    async def delete_users(self, user_ids):
        """"""
        sql = "DELETE FROM queued_users\n" \
              f"    WHERE lobby_id = $1 AND user_id::BIGINT = ANY(ARRAY{user_ids}::BIGINT[])\n" \
              "    RETURNING user_id;"
        return await G5.db.query(sql, self.id)

    async def clear_users(self):
        """"""
        sql = f"DELETE FROM queued_users WHERE lobby_id = $1;"
        await G5.db.query(sql, self.id)

    async def get_maps(self):
        """"""
        sql = "SELECT gm.*, lm.lobby_id\n" \
            "FROM lobby_maps lm\n" \
            "JOIN guild_maps gm\n" \
            "   ON lm.emoji_id = gm.emoji_id\n" \
            "WHERE lobby_id = $1;"
        maps_data = await G5.db.query(sql, self.id)
        maps = [Map.from_dict(data, self.guild) for data in maps_data]
        return [m for m in maps if m.emoji]

    async def clear_maps(self):
        """"""
        sql = "DELETE FROM lobby_maps WHERE lobby_id = $1;"
        await G5.db.query(sql, self.id)

    async def insert_maps(self, emojis_ids):
        """"""
        values = f", ".join(
            f"({self.id}, {emoji_id})" for emoji_id in emojis_ids)
        sql = f"INSERT INTO lobby_maps VALUES {values};"
        await G5.db.query(sql)

    async def get_cvars(self):
        """"""
        sql = "SELECT name, value FROM lobby_cvars WHERE lobby_id = $1;"
        query = await G5.db.query(sql, self.id)
        return {r['name']: r['value'] for r in query}

    async def insert_cvar(self, name, value):
        """"""
        sql = f"INSERT INTO lobby_cvars VALUES ($1, $2, $3);"
        await G5.db.query(sql, name, value, self.id)

    async def update_cvar(self, name, value):
        """"""
        sql = f"UPDATE lobby_cvars SET value = $1 WHERE name = $2 AND lobby_id = $3;"
        await G5.db.query(sql, value, name, self.id)

    async def delete_cvar(self, name):
        """"""
        sql = f"DELETE FROM lobby_cvars WHERE name = $1 AND lobby_id = $2;"
        await G5.db.query(sql, name, self.id)
