# mpoolView.py

import discord
import asyncio
from typing import List

from bot.helpers.models import MapModel
from bot.helpers.db import db


class MapButton(discord.ui.Button['MapPoolView']):
    def __init__(self, selected_map: MapModel, style: discord.ButtonStyle):
        super().__init__(style=style, label=selected_map.display_name)
        self.selected_map = selected_map

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_click_button(interaction, self)


class SaveButton(discord.ui.Button['MapPoolView']):
    def __init__(self):
        super().__init__(label="Save", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        if len(self.view.new_maps) != 7:
            await interaction.response.send_message("Must be exactly 7 activated maps.", ephemeral=True)
            return

        await db.update_lobby_maps(self.view.lobby_id, self.view.new_maps, self.view.existing_maps)
        embed = discord.Embed(title="Map pool updated successfully")
        await interaction.response.edit_message(embed=embed, view=None)
        try:
            self.view.future.set_result(None)
        except asyncio.InvalidStateError:
            pass


class DiscardButton(discord.ui.Button['MapPoolView']):
    def __init__(self):
        super().__init__(label="Discard", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Action discarded!")
        await interaction.response.edit_message(embed=embed, view=None)
        try:
            self.view.future.set_result(None)
        except asyncio.InvalidStateError:
            pass


class MapPoolView(discord.ui.View):
    def __init__(self,
                 lobby_id: int,
                 user: discord.Member,
                 guild_maps: List[MapModel],
                 existing_maps: List[MapModel],
                 timeout=180):
        """"""
        super().__init__(timeout=timeout)
        self.lobby_id = lobby_id
        self.user = user
        self.guild_maps = guild_maps
        self.existing_maps = existing_maps
        self.new_maps = existing_maps.copy()
        self.future = None

        for m in guild_maps:
            style = discord.ButtonStyle.primary if m in existing_maps else discord.ButtonStyle.secondary
            self.add_item(MapButton(m, style))

        self.add_item(SaveButton())
        self.add_item(DiscardButton())

    def embed_map_pool(self):
        """"""
        embed = discord.Embed(title="Map Pool")
        active_maps = ""
        inactive_maps = ""

        for m in self.guild_maps:
            if m in self.new_maps:
                active_maps += f"`{m.display_name}`\n"
            else:
                inactive_maps += f"`{m.display_name}`\n"

        if not inactive_maps:
            inactive_maps = "*Empty*"
        if not active_maps:
            active_maps = "*Empty*"

        embed.add_field(name="Active Maps", value=active_maps)
        embed.add_field(name="Inactive Maps", value=inactive_maps)
        return embed

    async def on_click_button(self, interaction: discord.Interaction, button: MapButton):
        """"""
        user = interaction.user
        selected_map = button.selected_map
        if self.user != user:
            await interaction.response.send_message("You don't have permission!", ephemeral=True)
            return

        if selected_map in self.new_maps:
            self.new_maps.remove(selected_map)
            button.style = discord.ButtonStyle.secondary
        else:
            self.new_maps.append(selected_map)
            button.style = discord.ButtonStyle.primary

        embed = self.embed_map_pool()
        await interaction.response.edit_message(embed=embed, view=self)

    async def start_mpool(self, interaction: discord.Interaction) -> None:
        """"""
        embed = self.embed_map_pool()
        await interaction.followup.send(embed=embed, ephemeral=True, view=self)

        self.future = asyncio.get_running_loop().create_future()
        try:
            await asyncio.wait_for(self.future, 180)
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timeout! Proccess took too long.")
            await interaction.response.edit_message(embed=embed, view=None)
