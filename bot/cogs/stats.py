# link.py

from typing import Optional

from discord.ext import commands
from discord import app_commands, Interaction, Member
from bot.helpers.db import db
from bot.helpers.errors import CustomError
from bot.helpers.utils import generate_statistics_img


class StatsCog(commands.Cog, name='Stats'):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Show your stats")
    @app_commands.describe(
        target='User to show their stats, leave this blank to show your stats instead.'
    )
    async def stats(self, interaction: Interaction, target: Optional[Member]):
        await interaction.response.defer(ephemeral=True)
        user = target or interaction.user
        user_model = await db.get_user_by_discord_id(user.id, self.bot)

        if not user_model:
            raise CustomError(
                f"No stats were recorded for {user.mention}")
        
        try:
            file = generate_statistics_img(user_model)
            await interaction.followup.send(file=file)
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
