# link.py

from typing import Optional

from discord.ext import commands
from discord import app_commands, Interaction, Member, Embed
from bot.helpers.db import db
from bot.helpers.errors import CustomError
from bot.views import ConfirmView
from bot.helpers.utils import generate_statistics_img


class StatsCog(commands.Cog, name='Stats'):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="view-stats", description="View your stats or target's stats")
    @app_commands.describe(
        target='User to view their stats, leave this blank to view your stats instead.'
    )
    async def view_stats(self, interaction: Interaction, target: Optional[Member]):
        await interaction.response.defer(ephemeral=True)
        user = target or interaction.user
        player_model = await db.get_player_by_discord_id(user.id, self.bot)

        if not player_model:
            raise CustomError(
                f"No statistics were recorded.")
        
        try:
            file = generate_statistics_img(player_model)
            await interaction.followup.send(file=file)
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)

    @app_commands.command(name="reset-stats", description="Reset your stats")
    async def reset_stats(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        player_model = await db.get_player_by_discord_id(user.id, self.bot)

        if not player_model:
            raise CustomError(
                f"You must be linked to use this command.")
        
        embed = Embed(description=f"Are you sure you want to reset your stats?")
        confirm = ConfirmView(interaction.user)
        await interaction.edit_original_response(embed=embed, view=confirm)
        await confirm.wait()

        if not confirm.accepted:
            raise CustomError("Reset stats rejected")
        
        try:
            await db.reset_user_stats(user.id)
            embed.description = "Your stats reset successfully."
        except Exception as e:
            embed.description = "Something went wront, please try again later."
            self.bot.logger.error(e, exc_info=1)
        
        await interaction.edit_original_response(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
