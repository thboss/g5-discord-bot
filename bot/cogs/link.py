# link.py

from asyncpg.exceptions import UniqueViolationError

from discord.ext import commands
from discord import app_commands, Embed, Interaction
from bot.helpers.db import db
from bot.helpers.errors import CustomError
from bot.helpers.utils import validate_steam


class LinkCog(commands.Cog, name='Link'):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='link', description='Link users to their Steam.')
    @app_commands.describe(
        steam='Steam ID or Steam profle link'
    )
    async def link(self, interaction: Interaction, steam: str):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if user_model:
            raise CustomError(
                f"Your account is already linked to Steam")

        steam_id = validate_steam(steam)

        try:
            await db.insert_user({
                'discord_id': user.id,
                'steam_id': f"'{steam_id}'",
            })
        except UniqueViolationError:
            raise CustomError(
                f"This Steam is linked to another user. Please try different Steam ID.")
        except Exception:
            raise CustomError("Something went wrong! Please try again later.")

        guild_model = await db.get_guild_by_id(interaction.guild_id, self.bot)
        await user.add_roles(guild_model.linked_role)

        embed = Embed(
            description=f"You have successfully linked your account to [Steam](https://steamcommunity.com/profiles/{steam_id}/)")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="unlink", description="Unlink users from their Steam")
    async def unlink(self, interaction: Interaction):
        """"""
        await interaction.response.defer(ephemeral=True)
        user = interaction.user

        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model:
            raise CustomError("Your account is not linked to Steam.")

        user_lobby = await db.get_user_lobby(user.id, interaction.guild)
        if user_lobby:
            raise CustomError(
                f"You can't unlink your account while you are in Lobby #{user_lobby.id}.")

        user_match = await db.get_user_match(user.id, interaction.guild)
        if user_match:
            raise CustomError(
                f"You can't unlink your account while you are in match #{user_match.id}")

        user_team = await db.get_user_team(user.id, interaction.guild)
        if user_team:
            raise CustomError(
                f"You can't unlink your account while you are in team #{user_team.id}")
        
        spectators = await db.get_spectators(interaction.guild)
        for spec in spectators:
            if spec.user == user:
                raise CustomError(
                    "You can't unlink your account while you are in spectators list.")

        try:
            await db.delete_user(user.id)
        except Exception as e:
            raise CustomError("Something went wrong! Please try again later.")

        guild_model = await db.get_guild_by_id(interaction.guild_id, self.bot)
        await user.remove_roles(guild_model.linked_role)

        embed = Embed(
            description="You have successfully unlinked your account.")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(LinkCog(bot))
