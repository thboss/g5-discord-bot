# bot/helpers/models/user.py

import discord
from typing import Optional


class UserModel:
    """"""

    def __init__(
        self,
        member: Optional[discord.Member],
        steam: Optional[str]
    ):
        """"""
        self.member = member
        self.steam = steam

    @classmethod
    def from_dict(cls, data: dict, member: discord.Member) -> "UserModel":
        """"""
        return cls(
            member,
            data['steam_id']
        )
