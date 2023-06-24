# bot.py


import logging
import os
import traceback

from discord.ext import commands
from discord import app_commands, Interaction, Embed, Guild

from .helpers.db import db
from .helpers.api import api
from .helpers.config_reader import Config
from .helpers.errors import CustomError, APIError


class G5Bot(commands.AutoShardedBot):
    """"""

    def __init__(self, intents: dict) -> None:
        super().__init__(command_prefix=commands.when_mentioned_or(
            Config.prefix), help_command=None, intents=intents)

        self.description = ""
        self.logger = logging.getLogger('Bot')
        self.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        """ Executed every time a normal valid command catches an error. """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, (CustomError, APIError)):
            embed = Embed(description=error.message, color=0xE02B2B)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            embed = Embed(
                description="You are missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to execute this command!",
                color=0xE02B2B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = Embed(
                title="Invalid Usage!",
                description=str(error),
                color=0xE02B2B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, commands.CommandNotFound):
            embed = Embed(
                description=f"Command **`{interaction.command.name}`** is not valid!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            self.log_exception(
                f'Unhandled exception in "{interaction.command.name}" command:', error)

    def log_exception(self, msg, error):
        """ Logs an exception. """
        logger_cog = self.get_cog('Logger')
        logger_cog.log_exception(msg, error)

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        """"""
        await db.connect()
        api.connect(self.loop)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        #  Sync guilds' information with the database.
        if self.guilds:
            await db.sync_guilds([g.id for g in self.guilds])
            for guild in self.guilds:
                await db.create_default_guild_maps(guild)
                await self.check_guild_requirements(guild)

        match_cog = self.get_cog("Match")
        if match_cog:
            if not match_cog.check_live_matches.is_running():
                match_cog.check_live_matches.start()

        # Sync slash commands
        guild = self.get_guild(Config.guild_id)
        await self.tree.sync(guild=guild)
        self.tree.copy_global_to(guild=guild)
        # Sync commands globally if enabled
        if Config.sync_commands_globally:
            self.logger.info("Syncing commands globally...")
            await self.tree.sync()

    @commands.Cog.listener()
    async def on_guild_join(self, guild) -> None:
        """"""
        await db.sync_guilds([g.id for g in self.guilds])
        await db.create_default_guild_maps(guild)
        await self.check_guild_requirements(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild) -> None:
        """"""
        await db.sync_guilds([g.id for g in self.guilds])

    async def close(self):
        """"""
        await super().close()
        await db.close()
        await api.close()

    async def load_cogs(self) -> None:
        """ Load extensions in the cogs folder. """
        _CWD = os.path.dirname(os.path.abspath(__file__))
        cogs = os.listdir(_CWD + "/cogs")
        # Move logger cog to the first element in the list to be loaded first.
        cogs.insert(0, cogs.pop(cogs.index('logger.py')))
        for file in cogs:
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"bot.cogs.{extension}")
                    self.logger.info(f"Loaded extension '{extension}'")
                except Exception as e:
                    traceback.print_exc()
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {extension}\n{exception}")

    async def check_guild_requirements(self, guild: Guild) -> None:
        """"""
        guild_model = await db.get_guild_by_id(guild.id, self)
        category = guild_model.category
        linked_role = guild_model.linked_role
        prematch_channel = guild_model.prematch_channel
        results_channel = guild_model.results_channel

        if any(x is None for x in [category, linked_role, prematch_channel, results_channel]):
            if not category:
                category = await guild.create_category_channel('G5')
            if not linked_role:
                linked_role = await guild.create_role(name='Linked')
            if not prematch_channel:
                prematch_channel = await guild.create_voice_channel(category=category, name='Pre-Match')
            if not results_channel:
                results_channel = await guild.create_text_channel(category=category, name='Results')
                await results_channel.set_permissions(guild.self_role, send_messages=True)
                await results_channel.set_permissions(guild.default_role, send_messages=False)

            dict_data = {
                'category': category.id,
                'linked_role': linked_role.id,
                'prematch_channel': prematch_channel.id,
                'results_channel': results_channel.id
            }
            await db.update_guild_data(guild.id, dict_data)
