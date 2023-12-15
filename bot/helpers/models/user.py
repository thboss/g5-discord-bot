# bot/helpers/models/user.py

import discord


class PlayerModel:
    """"""

    def __init__(
        self,
        discord: discord.Member,
        steam_id: int,
    ):
        """"""
        self.discord = discord
        self.steam_id = steam_id

    @classmethod
    def from_dict(cls, data: dict, bot) -> "PlayerModel":
        """"""
        return cls(
            bot.get_user(data['id']),
            data['steam_id']
        )
