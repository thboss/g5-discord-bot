# bot/helpers/models/map.py

import discord
from typing import Optional


class MapModel:
    """"""

    def __init__(
        self,
        display_name: str,
        dev_name: str,
        guild: Optional[discord.Guild],
        emoji: Optional[discord.Emoji],
        emoji_str: str
    ):
        """"""
        self.display_name = display_name
        self.dev_name = dev_name
        self.guild = guild
        self.emoji = emoji
        self.emoji_str = emoji_str

    def __eq__(self, other):
        if (isinstance(other, MapModel)):
            return (self.display_name, self.dev_name, self.emoji) == (other.display_name, other.dev_name, other.emoji)
        return False

    @classmethod
    def from_dict(cls, data: dict, guild: discord.Guild) -> "MapModel":
        """"""
        display_name = data['display_name']
        dev_name = data['dev_name']
        emoji = discord.utils.get(guild.emojis, id=data['emoji_id'])
        emoji_str = f'<:{dev_name}:{emoji.id}>' if emoji else None

        return cls(
            display_name,
            dev_name,
            guild,
            emoji,
            emoji_str
        )