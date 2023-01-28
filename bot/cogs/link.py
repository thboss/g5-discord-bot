# link.py

from discord.ext import commands
from steam.steamid import SteamID, from_url

from ..utils import Utils, DB
from ..resources import G5


class LinkCog(commands.Cog):
    """"""

    @commands.command(brief=Utils.trans('link-command-brief'),
                      usage='link <steam_id> {OPTIONAL flag_emoji}')
    @DB.Guild.is_guild_setup()
    async def link(self, ctx, steam_id=None, flag='🇻🇳'):
        """"""
        user = ctx.author
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        db_user = await DB.User.get_user_by_id(user.id, ctx.guild)
        db_match = await DB.Match.get_user_match(user.id, ctx.guild.id)
        db_lobby = await DB.Lobby.get_user_lobby(user.id, ctx.guild.id)

        if db_user and db_user.steam:
            if not db_lobby and not db_match:
                await user.add_roles(db_guild.linked_role)
            raise commands.CommandInvokeError(Utils.trans(
                'account-already-linked', db_user.steam))

        if not steam_id:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        try:
            steam = SteamID(steam_id)
        except:
            raise commands.CommandInvokeError(Utils.trans('invalid-steam-id'))

        if not steam.is_valid():
            steam = from_url(steam_id, http_timeout=15)
            if steam is None:
                steam = from_url(
                    f'https://steamcommunity.com/id/{steam_id}/', http_timeout=15)
                if steam is None:
                    raise commands.CommandInvokeError(
                        Utils.trans('invalid-steam-id'))

        if flag not in Utils.FLAG_CODES:
            raise commands.CommandInvokeError(
                Utils.trans('invalid-flag-emoji'))

        steam_user = await DB.User.get_user_by_steam_id(str(steam), ctx.guild)
        if steam_user:
            raise commands.CommandInvokeError(
                Utils.trans('steam-linked-to-another-user'))

        if db_user:
            await db_user.update({
                'steam_id': f"'{steam}'",
                'flag': f"'{Utils.FLAG_CODES[flag]}'"
            })
        else:
            await DB.User.insert_user({
                'discord_id': user.id,
                'steam_id': f"'{steam}'",
                'flag': f"'{Utils.FLAG_CODES[flag]}'"
            })

        await user.add_roles(db_guild.linked_role)
        embed = G5.bot.embed_template(description=Utils.trans(
            'link-steam-success', user.mention, steam))
        await ctx.send(embed=embed)
        Utils.clear_messages([ctx.message])

    @commands.command(brief=Utils.trans('command-unlink-brief'),
                      usage='unlink [OPTIONAL: mention_user]')
    @DB.Guild.is_guild_setup()
    async def unlink(self, ctx):
        """"""
        user = ctx.author
        mention_user = ctx.message.mentions[0] if ctx.message.mentions else None
        if mention_user:
            if not user.guild_permissions.administrator:
                raise commands.CommandInvokeError(
                    Utils.trans('unlink-only-admins'))
            user = mention_user

        db_user = await DB.User.get_user_by_id(user.id, ctx.guild)
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        db_team = await DB.Team.get_user_team(user.id, ctx.guild.id)
        db_match = await DB.Match.get_user_match(user.id, ctx.guild.id)
        db_lobby = await DB.Lobby.get_user_lobby(user.id, ctx.guild.id)

        if not db_user or not db_user.steam:
            raise commands.CommandInvokeError(Utils.trans('you-not-linked'))
        if db_team:
            raise commands.CommandInvokeError(Utils.trans(
                'cannot-unlink-in-team', user.display_name, db_team.name))
        if db_match:
            raise commands.CommandInvokeError(Utils.trans(
                'cannot-unlink-in-match', user.display_name, db_match.id))
        if db_lobby:
            raise commands.CommandInvokeError(Utils.trans(
                'cannot-unlink-in-lobby', user.display_name, db_lobby.id))

        await db_user.update({'steam_id': 'NULL'})
        await user.remove_roles(db_guild.linked_role)

        embed = G5.bot.embed_template(
            description=Utils.trans('unlink-steam-success', user.mention))
        await ctx.message.reply(embed=embed)
