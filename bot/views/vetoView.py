# vetoView.py

from discord import Interaction, Member, Message, ButtonStyle, Embed
from discord.ui import View, Button
import random
import asyncio
from typing import List, Literal

from bot.helpers.configs import Config


class MapButton(Button['VetoView']):
    def __init__(self, selected_map: str, display_name: str):
        super().__init__(style=ButtonStyle.secondary,
                         label=display_name)
        self.selected_map = selected_map

    async def callback(self, interaction: Interaction):
        await self.view.on_click_button(interaction, self)


class VetoView(View):
    def __init__(self,
        message: Message,
        mpool: List[str],
        series: Literal["bo1", "bo2", "bo3"],
        captain1: Member,
        captain2: Member,
        game_mode: Literal["competitive", "wingman"],
        timeout=180
    ):
        super().__init__(timeout=timeout)
        self.message = message
        self.series = series
        self.captains = [captain1, captain2]
        self.ban_order = '12' * 20
        self.ban_number = 0
        self.maps_left = mpool
        self.maps_pick = []
        self.maps_ban = []
        self.game_mode = game_mode
        for m in mpool:
            self.add_item(MapButton(m, Config.maps[game_mode][m]))

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
    
    async def on_timeout(self):
        raise asyncio.TimeoutError
    
    async def interaction_check(self, interaction: Interaction):
        await interaction.response.defer()
        if interaction.user != self._active_picker:
            return False
        return True

    def embed_veto(self, title: str="Map veto begun!"):
        """"""
        description = f"Series: {self.series}\n\n" \
            f"**Captain 1:** {self.captains[0].mention}\n" \
            f"**Captain 2:** {self.captains[1].mention}\n\n" \
            f"**Current Turn:** {self._active_picker.mention}\n" \
            f"**Method:** {self._current_method}"
        embed = Embed(title=title, description=description)
        return embed

    async def on_click_button(self, interaction: Interaction, button: MapButton):
        user = interaction.user
        selected_map = button.selected_map
        if selected_map not in self.maps_left:
            return
    
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

        if selected_map in self.maps_ban:
            button.style = ButtonStyle.danger
        elif selected_map in self.maps_pick:
            button.style = ButtonStyle.success
        button.disabled = True
        self.ban_number += 1

        title = f"Player {user.display_name} **{action}** map **{Config.maps[self.game_mode][selected_map]}**"
        embed = self.embed_veto(title)
        await self.message.edit(embed=embed, view=None if self.is_veto_done else self)

        if self.is_veto_done:
            self.stop()


