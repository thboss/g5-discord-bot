# logging.py

import __main__
import aiohttp
import asyncio
import discord
from discord.ext import commands
import logging
from logging import config
from os import path
import traceback

from ..resources import G5


LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'defaultNoDate': {
            'format': '[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
            'datefmt': '%H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'defaultNoDate',
            'level': 'INFO',
            'stream': 'ext://sys.stdout'
        },
        'file1': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'level': 'INFO',
            'filename': path.join(path.dirname(path.abspath(__main__.__file__)), 'info.log'),
            'maxBytes': 7340032,
            'encoding': 'utf-8'
        },
        'file2': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'level': 'ERROR',
            'filename': path.join(path.dirname(path.abspath(__main__.__file__)), 'error.log'),
            'maxBytes': 7340032,
            'encoding': 'utf-8'
        }
    },
    'loggers': {
        'G5': {
            'level': 'DEBUG'
        },
        'discord.client': {
            'level': 'INFO'
        },
        'discord.gateway': {
            'level': 'WARNING'
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': [
            'console',
            'file1',
            'file2'
        ]
    }
}

config.dictConfig(LOGGING_CONFIG)


def indent(string, n=4):
    """"""
    indent = ' ' * n
    return indent + string.replace('\n', '\n' + indent)


def log_lines(lvl, msg, *args, sub_lines=None, **kwargs):
    """"""
    if sub_lines is not None:
        longest_subl_pref = len(max(sub_lines.keys(), key=len))

        for prefix, suffix in sub_lines.items():
            msg += '\n    {:<{width}} {}'.format(
                prefix + ':', suffix, width=longest_subl_pref + 1)

    logging.getLogger('G5.bot').log(lvl, msg, *args, **kwargs)


class LoggingCog(commands.Cog):
    """ Does the console printing of the bot. """

    def __init__(self):
        """ Set bot attribute. """
        self.logger = logging.getLogger('G5.bot')

    async def update_status(self):
        """ Update bot's status when guilds change. """
        prefix = G5.bot.command_prefix
        prefix = prefix[0] if prefix is not str else prefix
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=f'in {len(G5.bot.guilds)} servers | {prefix}help'
        )
        await G5.bot.change_presence(activity=activity)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """ Log exceptions inside of commands. """
        if isinstance(error, (commands.MissingPermissions, commands.CommandInvokeError, commands.CheckFailure, commands.CommandNotFound)):
            return

        self.log_exception(
            f'Uncaught exception in "{ctx.command}" command:', error)

    def log_exception(self, msg, error):
        """"""
        msg += '\n\n'
        exc_lines = traceback.format_exception(
            type(error), error, error.__traceback__)
        exc = ''.join(exc_lines)
        self.logger.error(msg + indent(exc))

    @commands.Cog.listener()
    async def on_connect(self):
        lines_dict = {'Username': G5.bot.user.name, 'ID': G5.bot.user.id}
        log_lines(logging.INFO, 'Connected to Discord', sub_lines=lines_dict)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update_status()

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if not ctx.guild:
            return
        lines_dict = {
            'Caller': f'{ctx.author} ({ctx.author.id})', 'Guild': f'{ctx.guild} ({ctx.guild.id})'}
        log_lines(logging.INFO, 'Command "%s" issued',
                  ctx.command, sub_lines=lines_dict)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        log_lines(logging.INFO, 'Bot has been added to server "%s" (%s)',
                  guild.name, guild.id)
        await self.update_status()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        log_lines(
            logging.INFO, 'Bot has been removed from server "%s" (%s)', guild.name, guild.id)
        await self.update_status()


async def start_request_log(session, ctx, params):
    """"""
    ctx.start = asyncio.get_event_loop().time()
    logger = logging.getLogger('G5.api')
    logger.info(f'Sending {params.method} request to {params.url}')


async def end_request_log(session, ctx, params):
    """"""
    logger = logging.getLogger('G5.api')
    elapsed = asyncio.get_event_loop().time() - ctx.start
    logger.info(f'Response received from {params.url} ({elapsed:.2f}s)\n'
                f'    Status: {params.response.status}\n'
                f'    Reason: {params.response.reason}')
    resp_json = await params.response.json()
    logger.debug(f'Response JSON from {params.url}: {resp_json}')

TRACE_CONFIG = aiohttp.TraceConfig()
TRACE_CONFIG.on_request_start.append(start_request_log)
TRACE_CONFIG.on_request_end.append(end_request_log)
