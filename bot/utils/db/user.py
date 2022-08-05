# user.py

from ...resources import G5


class User:
    """"""

    def __init__(self, id, user, steam, flag):
        """"""
        self.id = id
        self.user = user
        self.steam = steam
        self.flag = flag

    @classmethod
    def from_dict(cls, user_data: dict, guild):
        """"""
        return cls(
            user_data['discord_id'],
            guild.get_member(user_data['discord_id']),
            user_data['steam_id'],
            user_data['flag']
        )

    @staticmethod
    async def get_user_by_id(user_id, guild):
        """"""
        sql = "SELECT * FROM users\n" \
            f"    WHERE discord_id = $1;"
        user_data = await G5.db.query(sql, user_id)
        if user_data:
            return User.from_dict(user_data[0], guild)

    @staticmethod
    async def get_user_by_steam_id(steam_id, guild):
        """"""
        sql = "SELECT * FROM users\n" \
            f"    WHERE steam_id = $1;"
        user_data = await G5.db.query(sql, steam_id)
        if user_data:
            return User.from_dict(user_data[0], guild)

    @staticmethod
    async def get_users(users, guild):
        """"""
        users_ids = [u.id for u in users]
        sql = "SELECT * FROM users\n" \
            "    WHERE discord_id = ANY($1::BIGINT[]) AND steam_id IS NOT NULL;"
        users_data = await G5.db.query(sql, users_ids)
        users_data.sort(key=lambda x: users_ids.index(x['discord_id']))
        return [User.from_dict(user_data, guild) for user_data in users_data]

    @staticmethod
    async def insert_user(data: dict):
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO users ({cols})\n" \
              f"    VALUES({vals})"
        await G5.db.query(sql)

    async def update(self, data: dict):
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = 'UPDATE users\n' \
            f'    SET {col_vals}\n' \
            f'    WHERE discord_id = $1;'
        await G5.db.query(sql, self.id)
