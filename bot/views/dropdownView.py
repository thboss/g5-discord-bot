# dropdownView.py

from discord.ui import Select, View
from discord import SelectOption, Interaction, Member
from typing import List

class DropDownItems(Select):
    """ A custom Select class for dropdown items. """

    def __init__(self, placeholder: str, options: List[SelectOption], min_values: int, max_values: int):
        """ Initialize the dropdown with placeholder text, options, and value limits. """
        super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, options=options)

    async def callback(self, interaction: Interaction):
        """ Handle the selection of dropdown options. """
        await interaction.response.defer()
        self.view.selected_options = self.values
        self.view.stop()

class DropDownView(View):
    """ A view that displays a dropdown menu for selection. """

    def __init__(self, author: Member, placeholder: str, options: List[SelectOption], min_values: int, max_values: int, timeout: float = 60.0):
        """ Initialize the view with an author, placeholder text, options, value limits, and a timeout. """
        super().__init__(timeout=timeout)
        self.author = author
        self.selected_options = None  # This will store the user's selected options
        # Add the dropdown item to the view.
        self.add_item(DropDownItems(placeholder, options, min_values, max_values))

    async def on_timeout(self):
        """ Handle the timeout event. """
        self.selected_options = []  # Default to an empty list on timeout
        self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        """ Check if the interacting user is the author. """
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True