# map.py

import discord


class Map:
    """"""

    def __init__(self, display_name, dev_name, guild, emoji, emoji_str):
        """"""
        self.display_name = display_name
        self.dev_name = dev_name
        self.guild = guild
        self.emoji = emoji
        self.emoji_str = emoji_str

    def __eq__(self, other):
        if (isinstance(other, Map)):
            return (self.display_name, self.dev_name, self.emoji) == (other.display_name, other.dev_name, other.emoji)
        return False

    @classmethod
    def from_dict(cls, map_data: dict, guild):
        """"""
        display_name = map_data['display_name']
        dev_name = map_data['dev_name']
        emoji = discord.utils.get(guild.emojis, id=map_data['emoji_id'])
        emoji_str = f'<:{dev_name}:{emoji.id}>' if emoji else None

        return cls(
            display_name,
            dev_name,
            guild,
            emoji,
            emoji_str
        )
