# link.py

from typing import Optional

from discord.ext import commands, tasks
from discord import app_commands, Interaction, Member, Embed
from bot.helpers.db import db
from bot.helpers.errors import CustomError
from bot.views import ConfirmView
from bot.helpers.utils import generate_statistics_img, generate_leaderboard_img


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
        user_model = await db.get_user_by_discord_id(user.id, self.bot)

        if not user_model:
            raise CustomError(
                f"You must be linked to use this command.")
        
        try:
            file = generate_statistics_img(user_model)
            await interaction.followup.send(file=file)
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)

    @app_commands.command(name="reset-stats", description="Reset your stats")
    async def reset_stats(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        user_model = await db.get_user_by_discord_id(user.id, self.bot)

        if not user_model:
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

    @tasks.loop(minutes=10.0)
    async def update_leaderboard(self):
        """"""
        for guild in self.bot.guilds:
            guild_model = await db.get_guild_by_id(guild.id, self.bot)

            leaderboard_channel = guild_model.leaderboard_channel
            if not leaderboard_channel:
                continue

            try:
                await leaderboard_channel.purge()
            except:
                pass
            
            try:
                leaderboard = await db.get_users(guild.members)
                leaderboard.sort(key=lambda u: u.elo, reverse=True)
                leaderboard = list(filter(lambda u: u.played_matches != 0, leaderboard))
                if leaderboard:
                    try:
                        file = generate_leaderboard_img(leaderboard[:10])
                        await leaderboard_channel.send(file=file)
                    except Exception as e:
                        self.bot.logger.error(e, exc_info=1)
            except:
                pass


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
