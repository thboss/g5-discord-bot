# vetoView.py

import discord
import asyncio
import random
from typing import List, Literal

from bot.helpers.models import MapModel


class MapButton(discord.ui.Button['VetoView']):
    def __init__(self, selected_map: MapModel):
        super().__init__(style=discord.ButtonStyle.secondary,
                         label=selected_map.display_name, emoji=selected_map.emoji)
        self.selected_map = selected_map

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        user = interaction.user
        view: VetoView = self.view

        if view._active_picker != user:
            await interaction.response.send_message("Its not your turn!", ephemeral=True)
            return

        title = view.process_click_button(user, self.selected_map)
        if self.selected_map in view.maps_ban:
            self.style = discord.ButtonStyle.danger
        elif self.selected_map in view.maps_pick:
            self.style = discord.ButtonStyle.success
        self.disabled = True

        if view.is_veto_done:
            view.stop()
            return

        embed = view.embed_veto(title)
        await interaction.response.edit_message(embed=embed, view=view)


class VetoView(discord.ui.View):
    def __init__(self, setup_message: discord.Message, mpool: List[MapModel], series: Literal["bo1", "bo2", "bo3"], captains: List[discord.Member], timeout=180):
        super().__init__(timeout=timeout)
        self.setup_message = setup_message
        self.series = series
        self.captains = captains
        self.ban_order = '12' * 10
        self.ban_number = 0
        self.maps_left = mpool
        self.maps_pick = []
        self.maps_ban = []
        self.future = None
        for m in mpool:
            self.add_item(MapButton(m))

    @property
    def _active_picker(self):
        picking_player_number = int(self.ban_order[self.ban_number])
        return self.captains[picking_player_number - 1]

    @property
    def _current_method(self):
        if self.series == 'bo3':
            if self.ban_number in [0, 1, 4, 5]:
                next_method = "Ban"
            elif self.ban_number in [2, 3]:
                next_method = "Pick"
            else:
                next_method = "None"
        elif self.series == 'bo2':
            if self.ban_number in [0, 1, 2, 3]:
                next_method = 'Ban'
            elif self.ban_number in [4, 5]:
                next_method = "Pick"
            else:
                next_method = "None"
        else:
            if len(self.maps_left) == 1:
                next_method = "None"
            else:
                next_method = "Ban"
        return next_method

    @property
    def is_veto_done(self):
        return (self.series == 'bo3' and len(self.maps_pick) == 3) or \
            (self.series == 'bo2' and len(self.maps_pick) == 2) or \
            (self.series == 'bo1' and len(self.maps_pick) == 1)

    def embed_veto(self, title: str = None):
        """"""
        if self.is_veto_done:
            desc = "**Picked Maps:**"
            for index, map in enumerate(self.maps_pick):
                desc += f"\n{index + 1}. {map.emoji} {map.display_name}"
        else:
            desc = f"Series: {self.series}\n\n" \
                f"**Captain 1:** {self.captains[0].mention}\n" \
                f"**Captain 2:** {self.captains[1].mention}\n\n" \
                f"**Captain Turn:** {self._active_picker.mention}\n" \
                f"**Method:** {self._current_method}"
        embed = discord.Embed(title=title, description=desc)
        return embed

    def process_click_button(self, user: discord.Member, selected_map: MapModel):
        self.maps_left.remove(selected_map)

        if self.series == 'bo3':
            if self.ban_number in [0, 1, 4, 5]:
                self.maps_ban.append(selected_map)
                action = 'banned'
            else:
                self.maps_pick.append(selected_map)
                action = 'picked'

            if self.ban_number == 5:
                self.maps_pick.append(random.choice(self.maps_left))

        elif self.series == 'bo2':
            if self.ban_number in [0, 1, 2, 3]:
                self.maps_ban.append(selected_map)
                action = 'banned'
            else:
                self.maps_pick.append(selected_map)
                action = 'picked'

        else:  # self.series == 'bo1'
            self.maps_ban.append(selected_map)
            action = 'banned'

            if len(self.maps_left) == 1:
                self.maps_pick.append(random.choice(self.maps_left))

        title = f"Player {user.display_name} **{action}** map **{selected_map.display_name}**"

        if self.is_veto_done and self.future is not None:
            try:
                self.future.set_result(None)
            except asyncio.InvalidStateError:
                pass
        else:
            self.ban_number += 1

        return title

    async def start_veto(self) -> List[MapModel]:
        """"""
        embed = self.embed_veto(title="Map veto begun!")
        await self.setup_message.edit(embed=embed, view=self)

        self.future = asyncio.get_running_loop().create_future()
        await asyncio.wait_for(self.future, 180)

        embed = self.embed_veto(title="Map veto ended!")
        await self.setup_message.edit(embed=embed, view=None)
        await asyncio.sleep(3)

        return self.maps_pick
