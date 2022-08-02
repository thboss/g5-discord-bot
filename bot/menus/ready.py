import discord
import asyncio

from .embeds import Embeds
from ..resources import G5


class ReadyUsers(discord.Message):
    def __init__(self, message, users):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.users = users
        self.reactors = None
        self.future = None

    async def _process_ready(self, payload):
        """"""
        if not payload.guild_id:
            return

        user = payload.member

        if payload.message_id != self.id or user == self.author:
            return

        if user not in self.users or str(payload.emoji) != '✅':
            await self.remove_reaction(payload.emoji, user)
            return

        self.reactors.add(user)
        await self.edit(embed=Embeds.ready(self.users, self.reactors))

        if self.reactors.issuperset(self.users):
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass

    async def _message_deleted(self, payload):
        """"""
        if payload.message_id != self.id:
            return

        try:
            self.future.set_exception(asyncio.TimeoutError)
        except asyncio.InvalidStateError:
            pass

    async def ready_up(self):
        """"""
        self.reactors = set()
        try:
            await self.clear_reactions()
            await self.add_reaction('✅')
            await self.edit(content='', embed=Embeds.ready(self.users, self.reactions))
        except discord.NotFound:
            return self.reactors

        self.future = G5.bot.loop.create_future()
        G5.bot.add_listener(self._process_ready, name='on_raw_reaction_add')
        G5.bot.add_listener(self._message_deleted,
                            name='on_raw_message_delete')
        try:
            await asyncio.wait_for(self.future, 60)
        except asyncio.TimeoutError:
            pass
        G5.bot.remove_listener(self._process_ready, name='on_raw_reaction_add')
        G5.bot.remove_listener(self._message_deleted,
                               name='on_raw_message_delete')

        try:
            await self.clear_reactions()
        except discord.NotFound:
            pass
        return self.reactors
