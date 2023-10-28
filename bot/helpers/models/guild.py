# bot/helpers/models/guild.py

import discord

from typing import Optional
from aiohttp import BasicAuth


class GuildModel:
    """ A class representing a guild configuration. """

    def __init__(
        self,
        guild: discord.Guild,
        linked_role: Optional[discord.Role],
        waiting_channel: Optional[discord.VoiceChannel],
        results_channel: Optional[discord.TextChannel],
        leaderboard_channel: Optional[discord.TextChannel],
        category: Optional[discord.CategoryChannel],
        dathost_email: Optional[str],
        dathost_password: Optional[str]
    ) -> None:
        self.guild = guild
        self.linked_role = linked_role
        self.waiting_channel = waiting_channel
        self.results_channel = results_channel
        self.leaderboard_channel = leaderboard_channel
        self.category = category
        self.dathost_auth = BasicAuth(dathost_email or "", dathost_password or "")

    @classmethod
    def from_dict(cls, data: dict, guild: discord.Guild) -> "GuildModel":

        return cls(
            guild,
            guild.get_role(data['linked_role']),
            guild.get_channel(data['waiting_channel']),
            guild.get_channel(data['results_channel']),
            guild.get_channel(data['leaderboard_channel']),
            guild.get_channel(data['category']),
            data['dathost_email'],
            data['dathost_password']
        )

