import discord
import asyncio
import random

from .embeds import Embeds
from ..utils import Utils
from ..resources import G5


class MapVeto(discord.Message):
    """"""

    def __init__(self, message, series, mpool):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.ban_order = '12' * 10
        self.ban_number = 0
        self.series = series
        self.mpool = mpool
        self.maps_left = {m.emoji_str: m for m in mpool}
        self.maps_pick = []
        self.maps_ban = []
        self.captains = None
        self.future = None

    @property
    def _active_picker(self):
        """"""
        picking_player_number = int(self.ban_order[self.ban_number])
        return self.captains[picking_player_number - 1]

    async def _process_ban(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        if user not in self.captains or str(reaction) not in [m for m in self.maps_left] or user != self._active_picker:
            await self.remove_reaction(reaction, user)
            return

        try:
            selected_map = self.maps_left.pop(str(reaction))
        except KeyError:
            return

        next_method, title = self.pick_ban_process(user, selected_map)

        if (self.series == 'bo5' and len(self.maps_pick) == 5) or \
           (self.series == 'bo3' and len(self.maps_pick) == 3) or \
           (self.series == 'bo2' and len(self.maps_pick) == 2) or \
           (self.series == 'bo1' and len(self.maps_pick) == 1):
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
        else:
            self.ban_number += 1
            await self.clear_reaction(selected_map.emoji)

        embed = Embeds.veto_maps(title, next_method, self.series, self.mpool, self.maps_pick,
                                 self.maps_ban, self.ban_number, self.ban_order, self.captains, self._active_picker)
        await self.edit(embed=embed)

    def pick_ban_process(self, user, map):
        """"""
        if self.series == 'bo5':
            if self.ban_number == 0:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-ban')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 1:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 2:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 3:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 4:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 5:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)
                self.maps_pick.append(random.choice(
                    list(self.maps_left.values())))

        elif self.series == 'bo3':
            if self.ban_number == 0:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-ban')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 1:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 2:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 3:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-ban')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 4:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-ban')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 5:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
                self.maps_pick.append(random.choice(
                    list(self.maps_left.values())))

        elif self.series == 'bo2':
            if self.ban_number == 0:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-ban')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 1:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-ban')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 2:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-ban')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 3:
                self.maps_ban.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-banned-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 4:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)
            elif self.ban_number == 5:
                self.maps_pick.append(map)
                next_method = Utils.trans('map-method-pick')
                title = Utils.trans('user-picked-map',
                                    user.display_name, map.display_name)

        elif self.series == 'bo1':
            self.maps_ban.append(map)
            next_method = Utils.trans('map-method-ban')
            title = Utils.trans('user-banned-map',
                                user.display_name, map.display_name)
            if len(self.maps_left) == 1:
                self.maps_pick.append(random.choice(
                    list(self.maps_left.values())))

        return next_method, title

    async def _message_deleted(self, message):
        """"""
        if message.id != self.id:
            return
        G5.bot.remove_listener(self._process_ban, name='on_reaction_add')
        G5.bot.remove_listener(
            self._message_deleted, name='on_message_delete')
        try:
            self.future.set_exception(ValueError)
        except asyncio.InvalidStateError:
            pass
        self.future.cancel()

    async def veto(self, captain_1, captain_2):
        """"""
        self.captains = [captain_1, captain_2]

        if len(self.mpool) % 2 == 0:
            self.captains.reverse()

        title = Utils.trans('map-bans-begun')
        method = Utils.trans('map-method-ban')
        embed = Embeds.veto_maps(title, method, self.series, self.mpool, self.maps_pick,
                                 self.maps_ban, self.ban_number, self.ban_order, self.captains, self._active_picker)
        await self.edit(embed=embed)

        for m in self.mpool:
            await self.add_reaction(m.emoji)

        self.future = G5.bot.loop.create_future()
        G5.bot.add_listener(self._process_ban, name='on_reaction_add')
        G5.bot.add_listener(self._message_deleted, name='on_message_delete')
        try:
            await asyncio.wait_for(self.future, 180)
        except asyncio.TimeoutError:
            G5.bot.remove_listener(self._process_ban, name='on_reaction_add')
            G5.bot.remove_listener(
                self._message_deleted, name='on_message_delete')
            await self.clear_reactions()
            raise

        G5.bot.remove_listener(self._process_ban, name='on_reaction_add')
        G5.bot.remove_listener(
            self._message_deleted, name='on_message_delete')

        await self.clear_reactions()
        await asyncio.sleep(2)
        return self.maps_pick
