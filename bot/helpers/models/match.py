# bot/helpers/models/match.py

import discord
from typing import Optional


class MatchModel:
    """"""

    def __init__(
        self,
        match_id: int,
        lobby_id: int,
        guild: Optional[discord.Guild],
        message_id: int,
        category: Optional[discord.CategoryChannel],
        team1_channel: Optional[discord.VoiceChannel],
        team2_channel: Optional[discord.VoiceChannel],
        team1_id: int,
        team2_id: int
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
    def from_dict(cls, data: dict, guild: discord.Guild) -> "MatchModel":
        """"""
        return cls(
            data['id'],
            data['lobby'],
            guild,
            data['message'],
            guild.get_channel(data['category']),
            guild.get_channel(data['team1_channel']),
            guild.get_channel(data['team2_channel']),
            data['team1_id'],
            data['team2_id']
        )