# lobby.py

import json
import discord
from discord.ext import commands

from collections import defaultdict
from asyncpg.exceptions import UniqueViolationError
import asyncio

from ..utils import Utils, API, DB
from ..menus import ReadyUsers, MapPool, Embeds
from ..resources import G5


class JoinError(ValueError):
    """ Raised when a player can't join lobby for some reason. """

    def __init__(self, message):
        """ Set message parameter. """
        self.message = message


class JoinTeamsLobby(discord.Message):
    """"""

    def __init__(self, message, db_lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.db_lobby = db_lobby

    async def _process_action(self, payload):
        """"""
        if not payload.guild_id:
            return

        user = payload.member

        if payload.message_id != self.id or user == self.author:
            return

        if str(payload.emoji) not in ['▶️', '↩️']:
            await self.remove_reaction(payload.emoji, user)
            return

        title = None
        db_team = None
        db_team1 = None
        db_team2 = None
        team1_users = []
        team2_users = []

        db_guild = await DB.Guild.get_guild_by_id(self.guild.id)
        self.db_lobby = await DB.Lobby.get_lobby_by_id(self.db_lobby.id, self.guild.id)
        db_team = await DB.Team.get_user_team(user.id, self.guild.id)
        db_team1 = await DB.Team.get_team_by_id(self.db_lobby.team1_id)
        db_team2 = await DB.Team.get_team_by_id(self.db_lobby.team2_id)
        try:
            team1_users = await db_team1.get_users()
        except Exception:
            pass
        try:
            team2_users = await db_team2.get_users()
        except Exception:
            pass

        if str(payload.emoji) == '▶️':
            if not db_team or user != db_team.captain:
                title = Utils.trans('user-not-captain', user.display_name)
            elif (db_team1 and db_team.id == db_team1.id) or (db_team2 and db_team.id == db_team2.id):
                title = Utils.trans('team-already-in-lobby', db_team.name)
            elif db_team1 and db_team2:
                title = Utils.trans('lobby-team-is-full', db_team.name)
            else:
                if not db_team1:
                    await self.db_lobby.update({'team1_id': db_team.id})
                elif not db_team2:
                    await self.db_lobby.update({'team2_id': db_team.id})

                await self.db_lobby.lobby_channel.set_permissions(db_team.role, connect=True)
                title = Utils.trans('team-joined-lobby', db_team.name)

        team1_id = db_team1.id if db_team1 else 0
        team2_id = db_team2.id if db_team2 else 0

        if str(payload.emoji) == '↩️':
            if not db_team or user != db_team.captain:
                title = Utils.trans('user-not-captain', user.display_name)
            elif db_team.id not in [team1_id, team2_id]:
                title = Utils.trans('team-not-in-lobby', db_team.name)
            else:
                if db_team1 and db_team.id == db_team1.id:
                    await self.db_lobby.update({'team1_id': 'NULL'})
                    await self.db_lobby.delete_users([u.id for u in team1_users])
                    for user in set(team1_users) & set(self.db_lobby.lobby_channel.members):
                        await user.move_to(db_guild.prematch_channel)

                elif db_team2 and db_team.id == db_team2.id:
                    await self.db_lobby.update({'team2_id': 'NULL'})
                    await self.db_lobby.delete_users([u.id for u in team2_users])
                    for user in set(team2_users) & set(self.db_lobby.lobby_channel.members):
                        await user.move_to(db_guild.prematch_channel)

                await self.db_lobby.lobby_channel.set_permissions(db_team.role, overwrite=None)
                title = Utils.trans('team-left-lobby', db_team.name)

        lobby_cog = G5.bot.get_cog('LobbyCog')
        await lobby_cog.update_queue_msg(self.db_lobby, title)

        await self.remove_reaction(payload.emoji, user)

    async def action(self):
        emojis = [r.emoji for r in self.reactions]
        for e in ['▶️', '↩️']:
            if e not in emojis:
                await self.add_reaction(e)

        if self.id not in G5.bot.message_listeners:
            G5.bot.add_listener(self._process_action,
                                name='on_raw_reaction_add')
            G5.bot.message_listeners.add(self.id)


class LobbyCog(commands.Cog):
    """"""

    def __init__(self):
        self.locked_lobby = {}
        self.locked_lobby = defaultdict(lambda: False, self.locked_lobby)
        self.updating_msg = {}
        self.updating_msg = defaultdict(lambda: False, self.updating_msg)

    @commands.command(brief=Utils.trans('lobby-info-command-brief'))
    async def info(self, ctx):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        lobby_maps = await db_lobby.get_maps()

        embed = Embeds.lobby_info(db_lobby, lobby_maps)
        await ctx.send(embed=embed)
        Utils.clear_messages([ctx.message])

    @commands.command(brief=Utils.trans('create-lobby-command-brief'),
                      usage='create-lobby <pug|teams>',
                      aliases=['create-lobby'])
    @commands.has_permissions(administrator=True)
    @DB.Guild.is_guild_setup()
    async def create_lobby(self, ctx, type=None):
        """"""
        if type and type.lower() == 'pug':
            pug = True
        elif type and type.lower() == 'teams':
            pug = False
        else:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        lobby_id = await DB.Lobby.insert_lobby({
            'guild': ctx.guild.id,
            'pug': pug
        })
        db_lobby = await DB.Lobby.get_lobby_by_id(lobby_id, ctx.guild.id)
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        category = await ctx.guild.create_category_channel(name=f"Lobby #{lobby_id} [PUBLIC]")
        queue_channel = await ctx.guild.create_text_channel(category=category, name='Setup')
        lobby_channel = await ctx.guild.create_voice_channel(category=category, name='Lobby', user_limit=10)

        try:
            await queue_channel.set_permissions(ctx.guild.self_role, send_messages=True)
            await lobby_channel.set_permissions(ctx.guild.self_role, connect=True)
        except discord.InvalidArgument:
            pass
        await queue_channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await lobby_channel.set_permissions(ctx.guild.default_role, connect=False)
        if pug:
            await lobby_channel.set_permissions(db_guild.linked_role, connect=True)

        await db_lobby.update({
            'category': category.id,
            'queue_channel': queue_channel.id,
            'lobby_channel': lobby_channel.id,
        })

        guild_maps = await db_guild.get_maps()
        await db_lobby.insert_maps([m.emoji.id for m in guild_maps][:18])

        await self.update_queue_msg(db_lobby)

        msg = Utils.trans('success-create-lobby', db_lobby.id)
        embed = G5.bot.embed_template(title=msg)
        await ctx.send(embed=embed)

    @commands.command(brief=Utils.trans('delete-lobby-command-brief'),
                      aliases=['delete-lobby'])
    async def deletelobby(self, ctx):
        """ Delete the lobby. """
        db_lobby = await self.ensure_lobby(ctx.channel)
        await db_lobby.delete()

        for chnl in [db_lobby.lobby_channel, db_lobby.queue_channel, db_lobby.category]:
            try:
                await chnl.delete()
            except (AttributeError, discord.NotFound):
                pass

    @commands.command(usage='add-cvar <key> <value>',
                      brief=Utils.trans('add-cvar-command-brief'),
                      aliases=['add-cvar', 'addcvar'])
    async def add_cvar(self, ctx, *args):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        if len(args) != 2:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        cvars = await db_lobby.get_cvars()
        name = args[0]
        value = args[1]
        if name in cvars:
            await db_lobby.update_cvar(name, value)
            title = Utils.trans('cvar-updated', name)
        else:
            await db_lobby.insert_cvar(name, value)
            title = Utils.trans('cvar-added', name)

        cvars[name] = value
        msg = Utils.trans('cvars-list', json.dumps(cvars, indent=2))
        embed = G5.bot.embed_template(title=title, description=msg)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(usage='delete-cvar <key>',
                      brief=Utils.trans('delete-cvar-command-brief'),
                      aliases=['delete-cvar', 'deletecvar'])
    async def delete_cvar(self, ctx, *args):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        if len(args) != 1:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        cvars = await db_lobby.get_cvars()
        name = args[0]
        if name in cvars:
            await db_lobby.delete_cvar(name)
            title = Utils.trans('cvar-deleted', name)
            cvars.pop(name)
        else:
            title = Utils.trans('cvar-not-found', name)

        msg = Utils.trans('cvars-list', json.dumps(cvars, indent=2))
        embed = G5.bot.embed_template(title=title, description=msg)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(brief=Utils.trans('empty-lobby-command-brief'))
    async def empty(self, ctx):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        await self._empty_lobby(db_lobby, db_guild.prematch_channel)
        embed = G5.bot.embed_template(title=Utils.trans('queue-emptied'))
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(usage='capacity <new capacity>',
                      brief=Utils.trans('command-cap-brief'))
    async def capacity(self, ctx, *args):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        try:
            new_cap = int(args[0])
        except (IndexError, ValueError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        if new_cap == db_lobby.capacity:
            raise commands.CommandInvokeError(
                Utils.trans('capacity-already', new_cap))

        if new_cap < 2 or new_cap > 32 or new_cap % 2 != 0:
            raise commands.CommandInvokeError(
                Utils.trans('capacity-out-range'))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        await self._empty_lobby(db_lobby, db_guild.prematch_channel, new_cap)

        msg = Utils.trans('set-capacity', new_cap)
        embed = G5.bot.embed_template(title=msg)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(usage='season <season_id>',
                      brief=Utils.trans('lobby-season-command-brief'))
    async def season(self, ctx, *args):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)

        try:
            season_id = int(args[0])
        except (IndexError, ValueError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        if season_id:
            try:
                season = await API.Seasons.get_season(season_id)
            except Exception as e:
                G5.bot.logger.info(str(e))
                raise commands.CommandInvokeError(str(e))

            if not season:
                raise commands.CommandInvokeError(
                    Utils.trans('season-not-found'))

        await db_lobby.update({'season_id': season_id})

        if season_id:
            msg = Utils.trans('lobby-season-changed', season.name)
        else:
            msg = Utils.trans('lobby-season-removed')
        embed = G5.bot.embed_template(title=msg)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(usage='teams {captains|autobalance|random}',
                      brief=Utils.trans('command-teams-brief'))
    async def teams(self, ctx, *args):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        try:
            new_method = args[0].lower()
        except (IndexError, ValueError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        curr_method = db_lobby.team_method
        valid_methods = ['captains', 'autobalance', 'random']

        if new_method not in valid_methods:
            raise commands.CommandInvokeError(Utils.trans(
                'team-valid-methods', valid_methods[0], valid_methods[1], valid_methods[2]))

        if curr_method == new_method:
            raise commands.CommandInvokeError(
                Utils.trans('team-method-already', new_method))

        await db_lobby.update({'team_method': f"'{new_method}'"})

        title = Utils.trans('set-team-method', new_method)
        embed = G5.bot.embed_template(title=title)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(usage='captains {volunteer|rank|random}',
                      brief=Utils.trans('command-captains-brief'))
    async def captains(self, ctx, *args):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        try:
            new_method = args[0].lower()
        except (IndexError, ValueError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        curr_method = db_lobby.captain_method
        valid_methods = ['volunteer', 'rank', 'random']

        if new_method not in valid_methods:
            raise commands.CommandInvokeError(Utils.trans(
                'captains-valid-method', valid_methods[0], valid_methods[1], valid_methods[2]))

        if curr_method == new_method:
            raise commands.CommandInvokeError(Utils.trans(
                'captains-method-already', new_method))

        await db_lobby.update({'captain_method': f"'{new_method}'"})

        title = Utils.trans('set-captains-method', new_method)
        embed = G5.bot.embed_template(title=title)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(usage='series {bo1|bo2|bo3|bo5}',
                      brief=Utils.trans('command-series-brief'))
    async def series(self, ctx, *args):
        """ Set series type of the lobby. """
        db_lobby = await self.ensure_lobby(ctx.channel)
        try:
            new_series = args[0].lower()
        except (IndexError, ValueError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        curr_series = db_lobby.series
        valid_values = ['bo1', 'bo2', 'bo3', 'bo5']

        if new_series not in valid_values:
            raise commands.CommandInvokeError(Utils.trans('series-valid-methods',
                                                          'bo1', 'bo2', 'bo3', 'bo5'))

        if curr_series == new_series:
            raise commands.CommandInvokeError(
                Utils.trans('series-value-already', new_series))

        await db_lobby.update({'series_type': f"'{new_series}'"})

        title = Utils.trans('set-series-value', new_series)
        embed = G5.bot.embed_template(title=title)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(usage='region {none|region_code}',
                      brief=Utils.trans('command-region-brief'))
    async def region(self, ctx, *args):
        """ Set or remove the region of the lobby. """
        db_lobby = await self.ensure_lobby(ctx.channel)
        try:
            new_region = args[0].upper()
        except (IndexError, ValueError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        curr_region = db_lobby.region
        valid_regions = list(Utils.FLAG_CODES.values())

        if new_region == 'NONE':
            new_region = None

        if new_region not in [None] + valid_regions:
            raise commands.CommandInvokeError(Utils.trans('region-not-valid'))

        if curr_region == new_region:
            raise commands.CommandInvokeError(
                Utils.trans('lobby-region-already', curr_region))

        region = f"'{new_region}'" if new_region else 'NULL'
        await db_lobby.update({'region': region})

        title = Utils.trans('set-lobby-region', new_region)
        embed = G5.bot.embed_template(title=title)
        message = await ctx.send(embed=embed)
        Utils.clear_messages([message, ctx.message])

    @commands.command(brief=Utils.trans('command-mpool-brief'))
    async def mpool(self, ctx):
        """"""
        db_lobby = await self.ensure_lobby(ctx.channel)
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        message = await ctx.send('Map Pool')
        guild_maps = await db_guild.get_maps()
        lobby_maps = await db_lobby.get_maps()
        menu = MapPool(
            message, ctx.author, db_lobby, guild_maps[:18], lobby_maps[:18])
        await menu.edit_map_pool()
        Utils.clear_messages([message, ctx.message])

    async def ensure_lobby(self, channel):
        """"""
        db_lobby = await DB.Lobby.get_lobby_by_text_channel(channel)
        if not db_lobby:
            raise commands.CommandInvokeError(
                Utils.trans('command-only-in-queue-channel'))
        return db_lobby

    async def _empty_lobby(self, db_lobby, channel, new_cap=None):
        """"""
        if self.locked_lobby[db_lobby.id]:
            raise commands.CommandInvokeError(
                Utils.trans('cannot-empty-lobby'))

        self.locked_lobby[db_lobby.id] = True

        update_dict = {'team1_id': 'NULL', 'team2_id': 'NULL'}
        if new_cap:
            update_dict['capacity'] = new_cap

        awaitables = [
            db_lobby.clear_users(),
            db_lobby.update(update_dict)
        ]
        for user in db_lobby.lobby_channel.members:
            awaitables.append(user.move_to(channel))
        if new_cap:
            awaitables.append(db_lobby.lobby_channel.edit(user_limit=new_cap))
        await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)

        self.locked_lobby[db_lobby.id] = False
        await self.update_queue_msg(db_lobby, Utils.trans('queue-emptied'))

    async def update_queue_msg(self, db_lobby, title=None):
        """"""
        if not (db_lobby.lobby_channel and db_lobby.queue_channel):
            return

        while True:
            if not self.updating_msg[db_lobby.id]:
                break
            await asyncio.sleep(0.01)

        self.updating_msg[db_lobby.id] = True
        db_lobby = await DB.Lobby.get_lobby_by_id(db_lobby.id, db_lobby.guild.id)
        queued_users = await db_lobby.get_users()

        if not db_lobby.pug:
            team1_users = []
            team2_users = []

            if not db_lobby.queue_channel or not db_lobby.lobby_channel:
                self.updating_msg[db_lobby.id] = False
                return

            db_team1 = await DB.Team.get_team_by_id(db_lobby.team1_id)
            db_team2 = await DB.Team.get_team_by_id(db_lobby.team2_id)
            if db_team1:
                team1_users = await db_team1.get_users()
            if db_team2:
                team2_users = await db_team2.get_users()
            embed = Embeds.teams_queue(
                db_lobby,
                title,
                db_team1,
                db_team2,
                set(team1_users) & set(queued_users),
                set(team2_users) & set(queued_users)
            )
        else:
            embed = Embeds.pug_queue(db_lobby, title, queued_users)

        try:
            msg = await db_lobby.queue_channel.fetch_message(db_lobby.message_id)
            await msg.edit(embed=embed)
        except:
            try:
                msg = await db_lobby.queue_channel.send(embed=embed)
                await db_lobby.update({'last_message': msg.id})
            except:
                pass

        if not db_lobby.pug:
            lobby_msg = JoinTeamsLobby(msg, db_lobby)
            await lobby_msg.action()

        self.updating_msg[db_lobby.id] = False

    async def _join_lobby(self, user, db_lobby):
        """"""
        awaitables = [
            DB.User.get_user_by_id(user.id, db_lobby.guild),
            DB.Match.get_user_match(user.id, db_lobby.guild.id),
            DB.Team.get_user_team(user.id, db_lobby.guild.id),
            db_lobby.get_users(),
        ]
        result = await asyncio.gather(*awaitables, loop=G5.bot.loop)
        db_user = result[0]
        db_match = result[1]
        db_team = result[2]
        queued_users = result[3]

        if not db_user or not db_user.steam:
            raise JoinError(Utils.trans(
                'lobby-user-not-linked', user.display_name))
        if db_match:
            raise JoinError(Utils.trans(
                'lobby-user-in-match', user.display_name))
        if user in queued_users:
            raise JoinError(Utils.trans(
                'lobby-user-in-lobby', user.display_name))
        if len(queued_users) >= db_lobby.capacity:
            raise JoinError(Utils.trans('lobby-is-full', user.display_name))

        if not db_lobby.pug:
            if not db_team or db_team.id not in [db_lobby.team1_id, db_lobby.team2_id]:
                raise JoinError(Utils.trans(
                    'not-member-of-teams', user.display_name))
            team_users = await db_team.get_users()
            team_count = len(set(queued_users) & set(team_users))
            if team_count == db_lobby.capacity / 2 - 1:
                await db_lobby.lobby_channel.set_permissions(
                    db_team.role, overwrite=None)
            elif team_count >= db_lobby.capacity / 2:
                raise JoinError(Utils.trans(
                    'team-is-full', user.display_name, db_team.name))

        try:
            await db_lobby.insert_user(user.id)
        except UniqueViolationError:
            raise JoinError(Utils.trans(
                'lobby-user-in-lobby', user.display_name))
        return queued_users + [user]

    async def check_ready(self, message, users, db_lobby, db_guild):
        """"""
        awaitables = []
        for user in users:
            awaitables.append(user.remove_roles(db_guild.linked_role))
        await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)

        menu = ReadyUsers(message, users)
        ready_users = await menu.ready_up()
        unreadied = set(users) - ready_users
        if unreadied:
            await db_lobby.delete_users([user.id for user in unreadied])
            awaitables = []
            for user in users:
                awaitables.append(user.add_roles(db_guild.linked_role))
            for user in unreadied:
                awaitables.append(user.move_to(db_guild.prematch_channel))
            if not db_lobby.pug:
                db_team1 = await DB.Team.get_team_by_id(db_lobby.team1_id)
                db_team2 = await DB.Team.get_team_by_id(db_lobby.team2_id)
                if db_team1:
                    team1_users = await db_team1.get_users()
                    if len(set(team1_users) & set(unreadied)) < db_lobby.capacity / 2:
                        awaitables.append(db_lobby.lobby_channel.set_permissions(
                            db_team1.role, connect=True))
                if db_team2:
                    team2_users = await db_team2.get_users()
                    if len(set(team2_users) & set(unreadied)) < db_lobby.capacity / 2:
                        awaitables.append(db_lobby.lobby_channel.set_permissions(
                            db_team2.role, connect=True))

            await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)
            await self.update_queue_msg(db_lobby)
            return False

        await db_lobby.clear_users()
        prepare_match_channel = await db_guild.guild.create_voice_channel(name='Preparing match..', category=db_lobby.category)
        for user in users:
            awaitables.append(user.move_to(prepare_match_channel))
        await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)
        await message.delete()

        return prepare_match_channel

    async def setup_match(self, db_lobby, queued_users, db_guild, match_msg, prepare_match_channel):
        """"""
        match_cog = G5.bot.get_cog('MatchCog')
        try:
            match_started = await match_cog.start_match(
                queued_users,
                db_lobby,
                db_guild,
                match_msg
            )
        except Exception as e:
            G5.bot.logger.info(str(e))
            match_started = False

        awaitables = []

        if match_started:
            if not db_lobby.pug:
                awaitables.append(db_lobby.update({'team1_id': 'NULL'}))
                awaitables.append(db_lobby.update({'team2_id': 'NULL'}))
        else:
            for user in queued_users:
                if db_lobby.pug:
                    awaitables.append(
                        user.add_roles(db_guild.linked_role))
                awaitables.append(
                    user.move_to(db_guild.prematch_channel))

            if not db_lobby.pug:
                db_team1 = await DB.Team.get_team_by_id(db_lobby.team1_id)
                db_team2 = await DB.Team.get_team_by_id(db_lobby.team2_id)
                if db_team1:
                    awaitables.append(db_lobby.lobby_channel.set_permissions(
                        db_team1.role, connect=True))
                if db_team2:
                    awaitables.append(db_lobby.lobby_channel.set_permissions(
                        db_team2.role, connect=True))

        await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)
        try:
            await prepare_match_channel.delete()
        except:
            pass
        return match_started

    @ commands.Cog.listener()
    async def on_voice_state_update(self, user, before, after):
        """"""
        if before.channel == after.channel:
            return

        if before.channel is not None:
            before_lobby = await DB.Lobby.get_lobby_by_voice_channel(before.channel)
            if before_lobby and not self.locked_lobby[before_lobby.id]:
                removed = await before_lobby.delete_users([user.id])

                if removed:
                    title = Utils.trans(
                        'lobby-user-removed', user.display_name)
                    if not before_lobby.pug:
                        db_team = await DB.Team.get_user_team(user.id, user.guild.id)
                        if db_team:
                            team_users = await db_team.get_users()
                            queued_users = await before_lobby.get_users()
                            team_count = len(set(queued_users)
                                             & set(team_users))
                            if team_count == before_lobby.capacity / 2 - 1:
                                await before_lobby.lobby_channel.set_permissions(
                                    db_team.role, connect=True)

                    await self.update_queue_msg(before_lobby, title)

        if after.channel is not None:
            after_lobby = await DB.Lobby.get_lobby_by_voice_channel(after.channel)
            if after_lobby and not self.locked_lobby[after_lobby.id]:
                try:
                    queued_users = await self._join_lobby(user, after_lobby)
                except JoinError as e:
                    title = e.message
                else:
                    title = Utils.trans('lobby-user-added', user.display_name)

                    if len(queued_users) == after_lobby.capacity:
                        self.locked_lobby[after_lobby.id] = True
                        db_guild = await DB.Guild.get_guild_by_id(after_lobby.guild.id)
                        if after_lobby.pug:
                            try:
                                await after_lobby.lobby_channel.set_permissions(db_guild.linked_role, connect=False)
                            except:
                                pass

                        try:
                            queue_msg = await after_lobby.queue_channel.fetch_message(after_lobby.message_id)
                            if not after_lobby.pug:
                                await queue_msg.delete()
                                raise
                        except:
                            queue_msg = await after_lobby.queue_channel.send('ready message..')
                            await after_lobby.update({'last_message': queue_msg.id})

                        prepare_match_channel = await self.check_ready(queue_msg, queued_users, after_lobby, db_guild)

                        if after_lobby.pug:
                            try:
                                await after_lobby.lobby_channel.set_permissions(db_guild.linked_role, connect=True)
                            except:
                                pass
                        self.locked_lobby[after_lobby.id] = False

                        if prepare_match_channel:
                            match_msg = await after_lobby.queue_channel.send(embed=G5.bot.embed_template(description='Match Setup Process..'))
                            await self.update_queue_msg(after_lobby)
                            await self.setup_match(after_lobby, queued_users, db_guild, match_msg, prepare_match_channel)

                        return

                await self.update_queue_msg(after_lobby, title)

    async def setup_lobbies(self, guild):
        """"""
        guild_lobbies = await DB.Lobby.get_guild_lobbies(guild)
        awaitables = []

        for db_lobby in guild_lobbies:
            awaitables.append(self.update_queue_msg(db_lobby))
            category = db_lobby.category
            queue_channel = db_lobby.queue_channel
            lobby_channel = db_lobby.lobby_channel
            update_stmt = {}
            if not category:
                category = await guild.create_category_channel(name=f"Lobby #{db_lobby.id} [PUBLIC]")
                update_stmt['category'] = category.id
            if not queue_channel:
                queue_channel = await guild.create_text_channel(category=category, name='Setup')
                update_stmt['queue_channel'] = queue_channel.id
            if not lobby_channel:
                lobby_channel = await guild.create_voice_channel(category=category, name='Lobby', user_limit=db_lobby.capacity)
                update_stmt['lobby_channel'] = lobby_channel.id
            if update_stmt:
                await db_lobby.update(update_stmt)

        if awaitables:
            asyncio.gather(*awaitables, loop=G5.bot.loop,
                           return_exceptions=True)

    @ commands.Cog.listener()
    async def on_member_remove(self, user):
        """"""
        user_lobby = await DB.Lobby.get_user_lobby(user.id, user.guild.id)
        if not user_lobby:
            return

        title = Utils.trans('lobby-user-removed', user.display_name)
        await user_lobby.delete_users([user.id])
        await self.update_queue_msg(user_lobby, title)
