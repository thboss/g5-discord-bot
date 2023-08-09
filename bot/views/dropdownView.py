# dropdownView.py

from discord.ui import Select, View
from discord import SelectOption, Interaction, Member

from typing import List


class DropDownItems(Select):
    """"""

    def __init__(self,
        placeholder: str,
        options: List[SelectOption],
        min_values: int,
        max_values: int
    ):
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        self.view.selected_options = self.values
        await self.view.stop()


class DropDownView(View):
    """ A view that displays drop down selectable items."""

    def __init__(
        self,
        author: Member,
        placeholder: str,
        options: List[SelectOption],
        min_values: int,
        max_values: int,
        timeout=60
    ):
        super().__init__(timeout=timeout)
        self.author = author
        self.selected_options = None
        self.add_item(DropDownItems(placeholder, options, min_values, max_values))
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                content="You are not allowed to interact with this!",
                ephemeral=True)
            return False
        return True
