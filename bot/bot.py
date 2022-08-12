# bot.py

import discord
from discord.ext import commands

from aiohttp import ClientSession, ClientTimeout

import json
import asyncio
import sys
import os
import logging
import Levenshtein as lev


from . import cogs
from .utils import Utils
from .resources import Sessions, Config, G5


_CWD = os.path.dirname(os.path.abspath(__file__))
INTENTS_JSON = os.path.join(_CWD, 'intents.json')


class G5Bot(commands.AutoShardedBot):
    """ Sub-classed AutoShardedBot modified to fit the needs of the application. """

    def __init__(self):
        """ Set attributes and configure bot. """
        # Call parent init
        with open(INTENTS_JSON) as f:
            intents_attrs = json.load(f)

        intents = discord.Intents(**intents_attrs)
        super().__init__(command_prefix=Config.prefixes,
                         case_insensitive=True, intents=intents)

        # Set constants
        self.color = 0x0086FF
        self.logger = logging.getLogger('G5.bot')

        # Add check to not respond to DM'd commands
        self.add_check(lambda ctx: ctx.guild is not None)

        # Trigger typing before every command
        self.before_invoke(commands.Context.trigger_typing)

        G5.bot = self

        # Add cogs
        for cog in cogs.__all__:
            self.add_cog(cog())

        self.message_listeners = set()

    async def on_error(self, event_method, *args, **kwargs):
        """"""
        try:
            logging_cog = self.get_cog('LoggingCog')
            exc_type, exc_value, traceback = sys.exc_info()
            logging_cog.log_exception(
                f'Uncaught exception when handling "{event_method}" event:', exc_value)
        except Exception as e:
            print(e)

    def embed_template(self, **kwargs):
        """ Implement the bot's default-style embed. """
        if 'color' not in kwargs:
            kwargs['color'] = self.color
        embed = discord.Embed(**kwargs)
        return embed

    async def send_dm(self, user, embed):
        """"""
        if not user:
            return

        dm_channel = user.dm_channel or await user.create_dm()
        try:
            message = await dm_channel.send(embed=embed)
        except discord.Forbidden:
            self.logger.info(
                f'Unable to send message to user: {user.display_name}')
        else:
            return message

    @commands.Cog.listener()
    async def on_connect(self):
        Sessions.requests = ClientSession(
            loop=self.loop,
            json_serialize=lambda x: json.dumps(x, ensure_ascii=False),
            timeout=ClientTimeout(total=5),
            trace_configs=[cogs.logging.TRACE_CONFIG]
        )

    @commands.Cog.listener()
    async def on_ready(self):
        """ Synchronize the guilds the bot is in with the guilds table. """
        match_cog = self.get_cog('MatchCog')
        stats_cog = self.get_cog('StatsCog')
        setup_cog = self.get_cog('SetupCog')
        start = asyncio.get_event_loop().time()
        if self.guilds:
            print('Synchronizing guilds...')
            await G5.db.sync_guilds(*(guild.id for guild in self.guilds))
            for guild in self.guilds:
                try:
                    await setup_cog.prepare_server(guild)
                except Exception as e:
                    G5.bot.logger.error(
                        f'Error on preparing server {guild.name} ({guild.id}):\n{e}')

        if not match_cog.check_live_matches.is_running():
            match_cog.check_live_matches.start()

        if not stats_cog.update_leaderboard.is_running():
            stats_cog.update_leaderboard.start()

        now = asyncio.get_event_loop().time()
        self.logger.info(f'guilds Synchronized ({now - start:.2f}s)')
        self.logger.info(
            f'Bot is ready to use in {len(self.guilds)} Discord servers.')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """ Insert the newly added guild to the guilds table. """
        await G5.db.sync_guilds(*(guild.id for guild in self.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """ Delete the recently removed guild from the guilds table. """
        await G5.db.sync_guilds(*(guild.id for guild in self.guilds))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """"""
        message = None
        if isinstance(error, commands.MissingPermissions):
            await ctx.trigger_typing()
            missing_perm = error.missing_perms[0].replace('_', ' ')
            embed = self.embed_template(title=Utils.trans(
                'command-required-perm', missing_perm), color=0xFF0000)
            message = await ctx.message.reply(embed=embed)

        if isinstance(error, commands.CommandInvokeError):
            await ctx.trigger_typing()
            embed = self.embed_template(
                title=str(error.original), color=0xFF0000)
            message = await ctx.message.reply(embed=embed)

        if isinstance(error, commands.CommandNotFound):
            # Get Levenshtein distance from commands
            in_cmd = ctx.invoked_with
            bot_cmds = list(self.commands)
            lev_dists = [lev.distance(in_cmd, str(
                cmd)) / max(len(in_cmd), len(str(cmd))) for cmd in bot_cmds]
            lev_min = min(lev_dists)

            # Prep help message title
            embed_title = Utils.trans('help-not-valid', ctx.message.content)
            prefixes = self.command_prefix
            # Prefix can be string or iterable of strings
            prefix = prefixes[0] if prefixes is not str else prefixes

            # Make suggestion if lowest Levenshtein distance is under threshold
            if lev_min <= 0.5:
                embed_title += Utils.trans('help-did-you-mean') + \
                    f' `{prefix}{bot_cmds[lev_dists.index(lev_min)]}`?'
            else:
                embed_title += Utils.trans('help-use-help', prefix)

            embed = self.embed_template(title=embed_title)
            message = await ctx.message.reply(embed=embed)

        Utils.clear_messages([message, ctx.message])

    def run(self):
        """ Override parent run to automatically include Discord token. """
        super().run(Config.discord_token)

    async def close(self):
        """ Override parent close to close the API session and G5.db connection pool. """
        await super().close()
        await G5.db.close()

        self.logger.info('Closing API helper client session')
        await Sessions.requests.close()
