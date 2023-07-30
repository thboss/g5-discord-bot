# readyView.py

import discord
import asyncio
from typing import List


class ReadyButton(discord.ui.Button['ReadyView']):
    def __init__(self):
        super().__init__(label="Ready", custom_id="ready")

    async def callback(self, interaction: discord.Interaction):
        await self.view.process_click_button(interaction)


class ReadyView(discord.ui.View):
    def __init__(self, users: List[discord.Member]):
        super().__init__(timeout=60.0)
        self.users = users
        self.reactors = set()
        self.message = None
        self.future = None
        self.add_item(ReadyButton())

    @property
    def all_ready(self):
        return self.reactors.issuperset(self.users)

    async def process_click_button(self, interaction: discord.Interaction):
        user = interaction.user
        if user not in self.users or user in self.reactors:
            await interaction.response.defer()
            return

        self.reactors.add(user)
        await self.message.edit(embed=self._embed_ready(),
                                view=None if self.all_ready else self)

        await interaction.response.defer()

        if self.all_ready:
            self.stop()
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass

    def _embed_ready(self):
        """"""
        mention_users = ""
        statuses = ""
        embed = discord.Embed(title="Lobby filled up.")

        for num, user in enumerate(self.users, start=1):
            mention_users += f"{num}. {user.mention}\n"
            if user in self.reactors:
                statuses += "✅\n "
            else:
                statuses += ":heavy_multiplication_x:\n "

        embed.add_field(name=" __Player__", value=mention_users)
        embed.add_field(name="__Status__", value=statuses)
        embed.set_footer(text="Click the button below when you are ready.")
        return embed

    async def ready_up(self, message: discord.Message):
        mentions_users = ''.join(u.mention for u in self.users)
        mentions_msg = await message.channel.send(content=mentions_users)
        self.message = await message.edit(embed=self._embed_ready(), view=self)
        self.future = asyncio.get_running_loop().create_future()

        try:
            await asyncio.wait_for(self.future, 60)
        except asyncio.TimeoutError:
            pass

        await asyncio.sleep(2)
        try:
            await mentions_msg.delete()
        except Exception:
            pass

        return self.reactors
