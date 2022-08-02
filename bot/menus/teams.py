import discord
import asyncio
from random import shuffle

from .embeds import Embeds
from ..utils import API, DB, Utils
from ..resources import G5


class PickTeams(discord.Message):
    """"""

    def __init__(self, message, users, lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.users = users
        self.lobby = lobby
        self.pick_emojis = dict(zip(Utils.EMOJI_NUMBERS[1:], users))
        self.pick_order = '1' + '2211' * 20
        self.pick_number = None
        self.users_left = None
        self.teams = None
        self.captains_emojis = None
        self.future = None
        self.title = None

    @property
    def _active_picker(self):
        """"""
        if self.pick_number is None:
            return None

        picking_team_number = int(self.pick_order[self.pick_number])
        picking_team = self.teams[picking_team_number - 1]

        if len(picking_team) == 0:
            return None

        return picking_team[0]

    def _pick_player(self, picker, pickee):
        """"""
        if picker == pickee:
            return False
        elif not self.teams[0]:
            picking_team = self.teams[0]
            self.captains_emojis.append(list(self.pick_emojis.keys())[
                                        list(self.pick_emojis.values()).index(picker)])
            self.users_left.remove(picker)
            picking_team.append(picker)
        elif self.teams[1] == [] and picker == self.teams[0][0]:
            return False
        elif self.teams[1] == [] and picker in self.teams[0]:
            return False
        elif not self.teams[1]:
            picking_team = self.teams[1]
            self.captains_emojis.append(list(self.pick_emojis.keys())[
                                        list(self.pick_emojis.values()).index(picker)])
            self.users_left.remove(picker)
            picking_team.append(picker)
        elif picker == self.teams[0][0]:
            picking_team = self.teams[0]
        elif picker == self.teams[1][0]:
            picking_team = self.teams[1]
        else:
            return False

        if picker != self._active_picker:
            return False

        if len(picking_team) > len(self.users) // 2:
            return False

        self.users_left.remove(pickee)
        picking_team.append(pickee)
        self.pick_number += 1
        return True

    async def _process_pick(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        pick = self.pick_emojis.get(str(reaction.emoji), None)

        if pick is None or pick not in self.users_left or user not in self.users:
            await self.remove_reaction(reaction, user)
            return

        if not self._pick_player(user, pick):
            await self.remove_reaction(reaction, user)
            return

        await self.clear_reaction(reaction.emoji)
        title = Utils.trans('team-picked',
                            user.display_name, pick.display_name)

        if len(self.users) - len(self.users_left) == 2:
            await self.clear_reaction(self.captains_emojis[0])
        elif len(self.users) - len(self.users_left) == 4:
            await self.clear_reaction(self.captains_emojis[1])

        if len(self.users_left) == 1:
            fat_kid_team = self.teams[0] if len(self.teams[0]) <= len(
                self.teams[1]) else self.teams[1]
            fat_kid_team.append(self.users_left.pop(0))
            embed = Embeds.pick_teams(
                self.teams, self.pick_emojis, self._active_picker, title)
            await self.edit(embed=embed)
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
            return

        if len(self.users_left) == 0:
            embed = Embeds.pick_teams(
                self.teams, self.pick_emojis, self._active_picker, title)
            await self.edit(embed=embed)
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
            return

        embed = Embeds.pick_teams(
            self.teams, self.pick_emojis, self._active_picker, title)
        await self.edit(embed=embed)

    async def _message_deleted(self, message):
        """"""
        if message.id != self.id:
            return
        G5.bot.remove_listener(self._process_pick, name='on_reaction_add')
        G5.bot.remove_listener(
            self._message_deleted, name='on_message_delete')
        try:
            self.future.set_exception(ValueError)
        except asyncio.InvalidStateError:
            pass
        self.future.cancel()

    async def draft(self, db_guild):
        """"""
        self.users_left = self.users.copy()
        self.teams = [[], []]
        self.pick_number = 0
        self.captains_emojis = []
        captain_method = self.lobby.captain_method

        if captain_method == 'rank':
            users = await DB.User.get_users(self.users_left, db_guild.guild)
            leaderboard = await API.PlayerStats.get_leaderboard(users)
            users_dict = dict(zip(leaderboard, self.users_left))
            players = list(users_dict.keys())
            players.sort(key=lambda x: x.elo)

            for team in self.teams:
                player = [players.pop()]
                captain = list(map(users_dict.get, player))
                self.users_left.remove(captain[0])
                team.append(captain[0])
                captain_emoji_index = list(
                    self.pick_emojis.values()).index(captain[0])
                self.captains_emojis.append(
                    list(self.pick_emojis.keys())[captain_emoji_index])

        if captain_method == 'random':
            temp_users = self.users_left.copy()
            shuffle(temp_users)

            for team in self.teams:
                captain = temp_users.pop()
                self.users_left.remove(captain)
                team.append(captain)
                captain_emoji_index = list(
                    self.pick_emojis.values()).index(captain)
                self.captains_emojis.append(
                    list(self.pick_emojis.keys())[captain_emoji_index])

        embed = Embeds.pick_teams(self.teams, self.pick_emojis,
                                  self._active_picker, Utils.trans('team-draft-begun'))
        await self.edit(embed=embed)

        if self.users_left:
            for emoji, user in self.pick_emojis.items():
                if user in self.users_left:
                    await self.add_reaction(emoji)

            self.future = G5.bot.loop.create_future()
            G5.bot.add_listener(self._process_pick, name='on_reaction_add')
            G5.bot.add_listener(self._message_deleted,
                                name='on_message_delete')
            try:
                await asyncio.wait_for(self.future, 180)
            except asyncio.TimeoutError:
                G5.bot.remove_listener(
                    self._process_pick, name='on_reaction_add')
                G5.bot.remove_listener(
                    self._message_deleted, name='on_message_delete')
                await self.clear_reactions()
                raise

            G5.bot.remove_listener(
                self._process_pick, name='on_reaction_add')
            G5.bot.remove_listener(
                self._message_deleted, name='on_message_delete')

        await self.clear_reactions()
        return self.teams
