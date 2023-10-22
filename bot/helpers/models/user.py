# bot/helpers/models/user.py

import discord
from typing import Optional


class UserModel:
    """"""

    def __init__(
        self,
        member: Optional[discord.Member],
        steam: Optional[str],
        kills: int,
        deaths: int,
        assists: int,
        headshots: int,
        k2: int,
        k3: int,
        k4: int,
        k5: int,
        wins: int,
        played_matches: int,
        elo: int
    ):
        """"""
        self.member = member
        self.steam = steam
        self.kills = kills
        self.deaths = deaths
        self.assists = assists
        self.headshots = headshots
        self.k2 = k2
        self.k3 = k3
        self.k4 = k4
        self.k5 = k5
        self.wins = wins
        self.played_matches = played_matches
        self.elo = elo

    @classmethod
    def from_dict(cls, data: dict, member: discord.Member) -> "UserModel":
        """"""
        return cls(
            member,
            data['steam_id'],
            data['kills'],
            data['deaths'],
            data['assists'],
            data['headshots'],
            data['k2'],
            data['k3'],
            data['k4'],
            data['k5'],
            data['wins'],
            data['played_matches'],
            data['elo']
        )
