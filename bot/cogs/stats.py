# link.py

from typing import Optional

from discord.ext import commands, tasks
from discord import app_commands, Interaction, Member
from bot.helpers.db import db
from bot.helpers.errors import CustomError
from bot.helpers.utils import generate_statistics_img, generate_leaderboard_img


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
