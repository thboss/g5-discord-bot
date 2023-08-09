# bot/helpers/models/team.py

import discord
from typing import Optional


class TeamModel:
    """ A class representing a team infomations. """

    def __init__(
        self,
        team_id: int,
        guild: discord.Guild,
        name: str,
        flag: str,
        captain: Optional[discord.Member],
        role: Optional[discord.Role]
    ):
        """"""
        self.id = team_id
        self.guild = guild
        self.name = name
        self.flag = flag
        self.captain = captain
        self.role = role

    @classmethod
    def from_dict(cls, team_data: dict, guild: discord.Guild):
        """"""
        return cls(
            team_data['id'],
            guild,
            team_data['name'],
            team_data['flag'],
            guild.get_member(team_data['captain']),
            guild.get_role(team_data['role'])
        )