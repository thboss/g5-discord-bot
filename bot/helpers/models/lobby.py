# bot/helpers/models/lobby.py

import discord
from typing import Literal, Optional


class LobbyModel:
    """ A class representing a lobby configuration. """

    def __init__(
        self,
        lobby_id: int,
        guild: Optional[discord.Guild],
        capacity: int,
        category: Optional[discord.CategoryChannel],
        text_channel: Optional[discord.TextChannel],
        voice_channel: Optional[discord.VoiceChannel],
        message_id: Optional[int],
        team_method: Literal["autobalance", "captains", "random"],
        captain_method: Literal["random", "volunteer", "rank"],
        map_method: Literal["random", "veto"],
        game_mode: Literal["competitive", "wingman"],
        connect_time: int,
        location: str
    ):
        """"""
        self.id = lobby_id
        self.guild = guild
        self.capacity = capacity
        self.category = category
        self.text_channel = text_channel
        self.voice_channel = voice_channel
        self.message_id = message_id
        self.team_method = team_method
        self.captain_method = captain_method
        self.map_method = map_method
        self.game_mode = game_mode
        self.connect_time = connect_time
        self.location = location

    @classmethod
    def from_dict(cls, data: dict, guild: discord.Guild) -> "LobbyModel":
        """"""
        return cls(
            data['id'],
            guild,
            data['capacity'],
            guild.get_channel(data['category']),
            guild.get_channel(data['queue_channel']),
            guild.get_channel(data['lobby_channel']),
            data['last_message'],
            data['team_method'],
            data['captain_method'],
            data['map_method'],
            data['game_mode'],
            data['connect_time'],
            data['location']
        )
