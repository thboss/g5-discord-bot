# readyView.py

from discord import Interaction, Member, TextChannel, ButtonStyle, Embed
from discord.ui import View, Button, button
from typing import List


class ReadyView(View):
    def __init__(self, users: List[Member], channel: TextChannel, timeout=60):
        super().__init__(timeout=timeout)
        self.users = users
        self.channel = channel
        self.ready_users = set()
        self.message = None

    @property
    def all_ready(self):
        return self.ready_users.issuperset(self.users)
    
    @button(label='Ready', style=ButtonStyle.secondary)
    async def ready(self, interaction: Interaction, button: Button):
        self.ready_users.add(interaction.user)
        await self.message.edit(embed=self._embed_ready())
        if self.all_ready:
            try:
                await self.message.delete()
            except:
                pass
            self.stop()

    async def on_timeout(self):
        try:
            await self.message.delete()
        except:
            pass

    async def interaction_check(self, interaction: Interaction):
        await interaction.response.defer()
        user = interaction.user
        if user not in self.users or user in self.ready_users:
            return False
        return True

    def _embed_ready(self):
        """"""
        mention_users = ""
        statuses = ""
        embed = Embed(title="Lobby filled up.")

        for num, user in enumerate(self.users, start=1):
            mention_users += f"{num}. {user.mention}\n"
            if user in self.ready_users:
                statuses += "✅\n "
            else:
                statuses += ":heavy_multiplication_x:\n "

        embed.add_field(name=" __Player__", value=mention_users)
        embed.add_field(name="__Status__", value=statuses)
        embed.set_footer(text="Click the button below when you are ready.")
        return embed
    
    async def start(self):
        self.message = await self.channel.send(
            content=''.join(u.mention for u in self.users),
            embed=self._embed_ready(),
            view=self
        )
