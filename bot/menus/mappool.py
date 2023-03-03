import discord
import asyncio

from .embeds import Embeds
from ..utils import Utils
from ..resources import G5


class MapPool(discord.Message):
    """"""

    def __init__(self, message, user, lobby, guild_maps, lobby_maps):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.user = user
        self.lobby = lobby
        self.guild_maps = guild_maps
        self.lobby_maps = lobby_maps
        self.map_pool = None
        self.active_maps = None
        self.inactive_maps = None
        self.future = None

    async def _process_pick(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author or user != self.user:
            return

        await self.remove_reaction(reaction, user)
        emoji = str(reaction.emoji)

        if emoji == '✅':
            if len(self.active_maps) >= 7 and self.future is not None:
                try:
                    self.future.set_result(
                        Utils.trans('lobby-map-pool-updated'))
                except asyncio.InvalidStateError:
                    pass
            return

        if emoji == '❌':
            if self.future is not None:
                try:
                    self.future.set_result(
                        'Process cancelled! Map pool is not updated.')
                except asyncio.InvalidStateError:
                    pass
            return

        if emoji in self.inactive_maps:
            self.active_maps[emoji] = self.inactive_maps[emoji]
            self.inactive_maps.pop(emoji)
            self.map_pool.append(self.active_maps[emoji].dev_name)
        elif emoji in self.active_maps:
            self.inactive_maps[emoji] = self.active_maps[emoji]
            self.active_maps.pop(emoji)
            self.map_pool.remove(self.inactive_maps[emoji].dev_name)

        await self.edit(embed=Embeds.map_pool(self.active_maps, self.inactive_maps))

    async def edit_map_pool(self):
        """"""
        self.map_pool = [m.dev_name for m in self.lobby_maps]
        self.active_maps = {
            m.emoji_str: m for m in self.guild_maps if m.dev_name in self.map_pool}
        self.inactive_maps = {
            m.emoji_str: m for m in self.guild_maps if m.dev_name not in self.map_pool}

        await self.edit(embed=Embeds.map_pool(self.active_maps, self.inactive_maps))

        awaitables = [self.add_reaction(m.emoji)
                      for m in self.guild_maps]
        await asyncio.gather(*awaitables)
        await self.add_reaction('✅')
        await self.add_reaction('❌')

        self.future = G5.bot.loop.create_future()
        G5.bot.add_listener(self._process_pick, name='on_reaction_add')

        try:
            msg = await asyncio.wait_for(self.future, 180)
        except asyncio.TimeoutError:
            msg = 'Timeout! Process took too long.'

        G5.bot.remove_listener(
            self._process_pick, name='on_reaction_add')

        if not self.future.cancelled() and self.future.result() == Utils.trans('lobby-map-pool-updated'):
            active_emojis_ids = [m.emoji.id for m in self.active_maps.values()]
            await self.lobby.clear_maps()
            await self.lobby.insert_maps(active_emojis_ids)

        embed = G5.bot.embed_template(title=msg)
        await self.edit(embed=embed)
        await self.clear_reactions()
