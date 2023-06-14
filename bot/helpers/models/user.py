# bot/helpers/models/user.py

import discord
from typing import Optional


class UserModel:
    """"""

    def __init__(
        self,
        user: Optional[discord.Member],
        steam: Optional[str],
        flag: Optional[str]
    ):
        """"""
        self.user = user
        self.steam = steam
        self.flag = flag

    @classmethod
    def from_dict(cls, data: dict, user: discord.Member) -> "UserModel":
        """"""
        return cls(
            user,
            data['steam_id'],
            data['flag']
        )
