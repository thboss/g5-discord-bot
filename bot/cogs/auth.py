from discord import app_commands, Embed, Interaction
from discord.ext import commands

from bot.helpers.api import api
from bot.helpers.db import db
from bot.helpers.errors import CustomError

class AuthCog(commands.Cog):
    """"""

    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(name="auth", description="Authorize Dathost credentials")
    @app_commands.describe(email="Your Dathost email", password="Your Dathost password")
    @app_commands.checks.has_permissions(administrator=True)
    async def auth(self, interaction: Interaction, email: str, password: str):
        """"""
        await interaction.response.defer(ephemeral=True)

        valid_credentials = await api.check_auth(email, password)
        if not valid_credentials:
            raise CustomError("Invalid credentials")
        
        await db.update_guild_data(interaction.guild.id, {'dathost_email': f"'{email}'", 'dathost_password': f"'{password}'"})

        embed = Embed(title="Authorized successfully")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AuthCog(bot))