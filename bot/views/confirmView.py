# confirmView.py

from discord.ui import View, Button, button
from discord import Interaction, Member, ButtonStyle


class ConfirmView(View):
    """ A view that displays two buttons for accept or reject an action. """

    def __init__(self, target_user: Member, timeout=60):
        super().__init__(timeout=timeout)
        self.target_user = target_user
        self.accepted = None

    @button(label='Accept', style=ButtonStyle.green)
    async def _accept(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        self.accepted = True
        self.stop()

    @button(label='Reject', style=ButtonStyle.red)
    async def _reject(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        self.accepted = False
        self.stop()

    async def interaction_check(self, interaction: Interaction):
        if interaction.user != self.target_user:
            await interaction.response.send_message(
                content="You are not allowed to interact with this!",
                ephemeral=True)
            return False
        return True