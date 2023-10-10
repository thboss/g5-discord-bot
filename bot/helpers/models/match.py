# bot/helpers/models/match.py

import discord
from typing import Optional


class MatchModel:
    """"""

    def __init__(
        self,
        match_id: int,
        guild: Optional[discord.Guild],
        text_channel: Optional[discord.TextChannel],
        message_id: int,
        category: Optional[discord.CategoryChannel],
        team1_channel: Optional[discord.VoiceChannel],
        team2_channel: Optional[discord.VoiceChannel],
        game_server_id: str
    ):
        """"""
        self.id = match_id
        self.guild = guild
        self.text_channel = text_channel
        self.message_id = message_id
        self.category = category
        self.team1_channel = team1_channel
        self.team2_channel = team2_channel
        self.game_server_id = game_server_id

    @classmethod
    def from_dict(cls, data: dict, guild: discord.Guild) -> "MatchModel":
        """"""
        return cls(
            data['id'],
            guild,
            guild.get_channel(data['channel']),
            data['message'],
            guild.get_channel(data['category']),
            guild.get_channel(data['team1_channel']),
            guild.get_channel(data['team2_channel']),
            data['game_server_id']
        )