# match.py

from ...resources import G5


class Match:
    """"""

    def __init__(
        self,
        match_id,
        lobby_id,
        guild,
        message_id,
        category,
        team1_channel,
        team2_channel,
        team1_id,
        team2_id
    ):
        """"""
        self.id = match_id
        self.lobby_id = lobby_id
        self.guild = guild
        self.message_id = message_id
        self.category = category
        self.team1_channel = team1_channel
        self.team2_channel = team2_channel
        self.team1_id = team1_id
        self.team2_id = team2_id

    @classmethod
    def from_dict(cls, match_data: dict):
        """"""
        guild = G5.bot.get_guild(match_data['guild'])
        return cls(
            match_data['id'],
            match_data['lobby'],
            guild,
            match_data['message'],
            guild.get_channel(match_data['category']),
            guild.get_channel(match_data['team1_channel']),
            guild.get_channel(match_data['team2_channel']),
            match_data['team1_id'],
            match_data['team2_id']
        )

    @staticmethod
    async def get_match_by_id(match_id: int):
        """"""
        sql = "SELECT * FROM matches\n" \
            f"    WHERE id = $1;"
        match_data = await G5.db.query(sql, match_id)
        if match_data:
            return Match.from_dict(match_data[0])

    @staticmethod
    async def get_all_matches():
        """"""
        sql = "SELECT * FROM matches;"
        matches_data = await G5.db.query(sql)
        return [Match.from_dict(match_data) for match_data in matches_data]

    @staticmethod
    async def get_user_match(user_id, guild_id):
        """"""
        sql = "SELECT m.* FROM match_users mu\n" \
            "JOIN matches m\n" \
            "    ON mu.match_id = m.id AND m.guild = $1\n" \
            "WHERE mu.user_id = $2;"
        match_data = await G5.db.query(sql, guild_id, user_id)
        if match_data:
            return Match.from_dict(match_data[0])

    @staticmethod
    async def get_team_match(team_id):
        """"""
        sql = "SELECT * FROM matches\n" \
              "    WHERE team1_id = $1 OR team2_id = $2"
        query = await G5.db.query(sql, team_id, team_id)
        if query:
            return Match.from_dict(query[0])

    @staticmethod
    async def insert_match(data: dict):
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO matches ({cols})\n" \
              f"    VALUES({vals});"
        await G5.db.query(sql)
        return await Match.get_match_by_id(data['id'])

    async def insert_users(self, user_ids):
        """"""
        values = f", ".join(
            f"({self.id}, {user_id})" for user_id in user_ids)
        sql = f"INSERT INTO match_users VALUES {values};"
        await G5.db.query(sql)

    async def insert_user(self, user_id: int):
        """"""
        sql = "INSERT INTO match_users (match_id, user_id)\n" \
              f"    VALUES($1, $2);"
        await G5.db.query(sql, self.id, user_id)

    async def delete_user(self, user_id: int):
        """"""
        sql = "DELETE FROM match_users\n" \
              f"    WHERE match_id = $1 AND user_id = $2;"
        await G5.db.query(sql, self.id, user_id)

    async def delete_match(self):
        """"""
        sql = f"DELETE FROM matches WHERE id = $1;"
        await G5.db.query(sql, self.id)

    async def get_users(self):
        """"""
        sql = "SELECT user_id FROM match_users\n" \
              f"    WHERE match_id = $1;"
        query = await G5.db.query(sql, self.id)
        users_ids = list(map(lambda r: r['user_id'], query))
        match_users = []
        for uid in users_ids:
            user = self.guild.get_member(uid)
            if user:
                match_users.append(user)
            else:
                await self.delete_user(uid)
        return match_users
