
from ...resources import G5


class Team:
    """"""

    def __init__(
        self,
        team_id,
        guild,
        message_id,
        captain,
        name,
        flag,
        role
    ):
        """"""
        self.id = team_id
        self.guild = guild
        self.message_id = message_id
        self.captain = captain
        self.name = name
        self.flag = flag
        self.role = role

    @classmethod
    def from_dict(cls, team_data: dict):
        """"""
        guild = G5.bot.get_guild(team_data['guild'])
        return cls(
            team_data['id'],
            guild,
            team_data['message'],
            guild.get_member(team_data['captain']),
            team_data['name'],
            team_data['flag'],
            guild.get_role(team_data['role']),
        )

    @staticmethod
    async def get_team_by_id(team_id: int):
        """"""
        sql = "SELECT * FROM teams WHERE id = $1;"
        team_data = await G5.db.query(sql, team_id)
        if team_data:
            return Team.from_dict(team_data[0])

    @staticmethod
    async def get_team_by_role(role_id: int):
        """"""
        sql = "SELECT * FROM teams WHERE role = $1;"
        team_data = await G5.db.query(sql, role_id)
        if team_data:
            return Team.from_dict(team_data[0])

    @staticmethod
    async def get_team_by_message(message_id: int):
        """"""
        sql = "SELECT * FROM teams WHERE message = $1;"
        team_data = await G5.db.query(sql, message_id)
        if team_data:
            return Team.from_dict(team_data[0])

    @staticmethod
    async def get_user_team(user_id, guild_id):
        """"""
        sql = "SELECT t.* FROM team_users tu\n" \
            "JOIN teams t\n" \
            "    ON tu.team_id = t.id AND t.guild = $1\n" \
            "WHERE tu.user_id = $2;"
        team_data = await G5.db.query(sql, guild_id, user_id)
        if team_data:
            return Team.from_dict(team_data[0])

    @staticmethod
    async def get_guild_teams(guild_id):
        """"""
        sql = "SELECT * FROM teams WHERE guild = $1;"
        teams_data = await G5.db.query(sql, guild_id)
        return [Team.from_dict(team) for team in teams_data]

    @staticmethod
    async def insert(data: dict):
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO teams ({cols})\n" \
              f"    VALUES({vals})\n" \
            "RETURNING id;"
        team = await G5.db.query(sql)
        return list(map(lambda r: r['id'], team))[0]

    async def update(self, data: dict):
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = "UPDATE teams\n" \
              f"    SET {col_vals}\n" \
              f"    WHERE id = $1;"
        await G5.db.query(sql, self.id)

    async def delete(self):
        """"""
        sql = "DELETE FROM teams WHERE id = $1;"
        await G5.db.query(sql, self.id)

    async def get_users(self):
        """"""
        query = await G5.db.query(
            "SELECT user_id FROM team_users WHERE team_id = $1;", self.id
        )
        users_ids = list(map(lambda r: r['user_id'], query))
        team_members = []
        for uid in users_ids:
            user = self.guild.get_member(uid)
            if user:
                team_members.append(user)
            else:
                await self.delete_users([uid])
        return team_members

    async def insert_user(self, user_id: int):
        """"""
        sql = "INSERT INTO team_users (team_id, user_id)\n" \
              f"    VALUES($1, $2);"
        await G5.db.query(sql, self.id, user_id)

    async def delete_users(self, user_ids):
        """"""
        sql = "DELETE FROM team_users\n" \
              f"    WHERE team_id = $1 AND user_id::BIGINT = ANY(ARRAY{user_ids}::BIGINT[])\n" \
              "    RETURNING user_id;"
        return await G5.db.query(sql, self.id)
