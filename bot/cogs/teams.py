# teams.py

import discord
from discord.ext import commands
import asyncio

from ..utils import Utils, API, DB
from ..resources import G5

request_join_users = set()


async def generate_team_msg(db_team, db_guild, update=True):
    """"""
    if not db_guild.teams_channel:
        G5.bot.logger.info(
            f'Unable to update message for team #{db_team.id}: teams channel not found!')
        return

    title = f"{Utils.trans('team')} {db_team.name} {list(Utils.FLAG_CODES.keys())[list(Utils.FLAG_CODES.values()).index(db_team.flag)]} (#{db_team.id})"
    msg = f"\n\n**{Utils.trans('players')}:**\n"

    team_users = await db_team.get_users()
    for index, user in enumerate(team_users, start=1):
        if user == db_team.captain:
            msg += f'{index}. {user.mention if user else "Deleted User"} `👑`\n'
        else:
            msg += f'{index}. {user.mention if user else "Deleted User"}\n'

    embed = G5.bot.embed_template(title=title, description=msg)
    embed.set_footer(text=Utils.trans('team-message-footer'))
    try:
        join_team_msg = await db_guild.teams_channel.fetch_message(db_team.message_id)
        if update:
            await join_team_msg.edit(embed=embed)
    except discord.HTTPException:
        join_team_msg = await db_guild.teams_channel.send(embed=embed)
        await db_team.update({'message': join_team_msg.id})

    menu = TeamMessage(join_team_msg)
    await menu.action()


async def disband_team(db_team, db_guild):
    try:
        message = await db_guild.teams_channel.fetch_message(db_team.message_id)
        await message.delete()
    except Exception:
        pass

    msg = Utils.trans('team-disbanded', db_team.name)
    team_users = await db_team.get_users()
    await db_team.delete()

    embed = G5.bot.embed_template(title=msg)
    for user in team_users:
        await G5.bot.send_dm(user, embed)

    try:
        await API.Teams.delete_team(db_guild.headers, db_team.id)
    except Exception as e:
        G5.bot.logger.info(str(e))

    try:
        await db_team.role.delete()
    except Exception:
        pass


async def remove_team_member(db_team, db_user, db_guild):
    """"""
    user = db_user.user
    try:
        await API.Teams.remove_team_member(db_guild.headers, db_team.id, db_user)
    except Exception as e:
        G5.bot.logger.info(str(e))

    await db_team.delete_users([db_user.id])
    try:
        await user.remove_roles(db_team.role)
    except Exception:
        pass

    user_msg = Utils.trans('leave-team-success', db_team.name)
    embed = G5.bot.embed_template(title=user_msg)
    await G5.bot.send_dm(user, embed)

    captain_msg = Utils.trans('player-left-your-team',
                              user.display_name, db_team.name)
    embed = G5.bot.embed_template(title=captain_msg)
    await G5.bot.send_dm(db_team.captain, embed)

    await generate_team_msg(db_team, db_guild)


class TeamMessage(discord.Message):
    def __init__(self, message):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

    async def _process_action(self, payload):
        """"""
        if not payload.guild_id:
            return

        user = payload.member

        if payload.message_id != self.id or user == self.author:
            return

        await self.remove_reaction(payload.emoji, user)

        if str(payload.emoji) not in ['▶️', '↩️']:
            return

        curr_team = None
        db_guild = await DB.Guild.get_guild_by_id(self.guild.id)
        db_team = await DB.Team.get_team_by_message(
            self.id)
        db_user = await DB.User.get_user_by_id(user.id, self.guild)
        error_msg = None

        if str(payload.emoji) == '▶️':
            if db_user and db_user.steam:
                curr_team = await DB.Team.get_user_team(user.id, self.guild.id)
            if user in request_join_users:
                error_msg = Utils.trans('unable-to-send-join-team')
            elif not db_user or not db_user.steam:
                error_msg = Utils.trans('join-team-not-linked')
            elif curr_team:
                error_msg = Utils.trans('already-in-team')
            else:
                user_msg = Utils.trans('sent-request-join-team',
                                       db_team.name, db_team.captain.display_name)
                embed = G5.bot.embed_template(title=user_msg)
                embed.set_footer(
                    text=Utils.trans('request-join-team-footer'))
                await G5.bot.send_dm(user, embed)

                captain_msg = Utils.trans('player-ask-join-team',
                                          user.display_name, db_team.name)
                embed = G5.bot.embed_template(title=captain_msg)
                request_join_msg = await G5.bot.send_dm(db_team.captain, embed)

                if request_join_msg:
                    request_join_users.add(user)
                    menu = RequestJoinMessage(request_join_msg, user, db_team)
                    await menu.confirm()

        if str(payload.emoji) == '↩️':
            team_users = await db_team.get_users()
            db_lobby = await DB.Lobby.get_user_lobby(user.id, self.guild.id)
            db_match = await DB.Match.get_user_match(user.id, self.guild.id)
            if user not in team_users:
                error_msg = Utils.trans('player-not-in-team', db_team.name)
            elif db_lobby:
                error_msg = Utils.trans(
                    'cannot-leave-team-in-lobby', db_team.name, db_lobby.id)
            elif db_match:
                error_msg = Utils.trans(
                    'cannot-leave-team-in-match', db_team.name, db_match.id)
            elif user == db_team.captain:
                error_msg = Utils.trans(
                    'team-creator-cannot-leave', db_team.name)
            else:
                await remove_team_member(db_team, db_user, db_guild)

        if error_msg:
            embed = G5.bot.embed_template(title=error_msg)
            await G5.bot.send_dm(user, embed)

    async def action(self):
        emojis = [r.emoji for r in self.reactions]
        for e in ['▶️', '↩️']:
            if e not in emojis:
                await self.add_reaction(e)

        if self.id not in G5.bot.message_listeners:
            G5.bot.add_listener(self._process_action,
                                name='on_raw_reaction_add')
            G5.bot.message_listeners.add(self.id)


class RequestJoinMessage(discord.Message):
    def __init__(self, message, sender, db_team):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.sender = sender
        self.db_team = db_team
        self.future = None

    async def _process_request(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        if reaction.emoji not in ['✅', '❌']:
            return

        if self.sender in request_join_users:
            request_join_users.remove(self.sender)

        db_guild = await DB.Guild.get_guild_by_id(self.db_team.guild.id)
        self.db_team = await DB.Team.get_team_by_id(self.db_team.id)

        if not self.db_team:
            msg = Utils.trans('unable-add-user-team-removed')
            embed = G5.bot.embed_template(title=msg)
            await G5.bot.send_dm(user, embed)
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
            await self.delete()
            return

        if reaction.emoji == '✅':
            db_user = await DB.User.get_user_by_id(self.sender.id, self.db_team.guild)

            try:
                await API.Teams.add_team_member(db_guild.headers, self.db_team.id, db_user.steam, self.sender.display_name)
            except Exception as e:
                G5.bot.logger.info(str(e))
                embed = G5.bot.embed_template(description=str(e))
                await G5.bot.send_dm(user, embed)
                if self.future is not None:
                    try:
                        self.future.set_result(None)
                    except asyncio.InvalidStateError:
                        pass
                return

            await self.db_team.insert_user(self.sender.id)
            await self.sender.add_roles(self.db_team.role)

            msg = Utils.trans('approved-join-team-member',
                              self.sender.display_name, self.db_team.name)
            embed = G5.bot.embed_template(title=msg)
            await G5.bot.send_dm(user, embed)

            msg = Utils.trans('accepted-join-team', self.db_team.name)
            embed = G5.bot.embed_template(title=msg)
            await G5.bot.send_dm(self.sender, embed)

            try:
                await self.db_team.guild.add_roles(self.db_team.role)
            except Exception:
                pass

            await generate_team_msg(self.db_team, db_guild)

            G5.bot.remove_listener(
                self._process_request, name='on_reaction_add')

        if reaction.emoji == '❌':
            msg = Utils.trans('declined-join-team-member',
                              self.sender.display_name, self.db_team.name)
            embed = G5.bot.embed_template(title=msg)
            await G5.bot.send_dm(user, embed)

            msg = Utils.trans('you-declined-join-team', self.db_team.name)
            embed = G5.bot.embed_template(title=msg)
            await G5.bot.send_dm(self.sender, embed)

            G5.bot.remove_listener(
                self._process_request, name='on_reaction_add')

        if self.future is not None:
            try:
                self.future.set_result(None)
            except asyncio.InvalidStateError:
                pass

    async def confirm(self):
        await self.add_reaction('✅')
        await self.add_reaction('❌')

        self.future = G5.bot.loop.create_future()
        G5.bot.add_listener(self._process_request, name='on_reaction_add')

        try:
            await asyncio.wait_for(self.future, 3600)
        except asyncio.TimeoutError:
            G5.bot.remove_listener(
                self._process_request, name='on_reaction_add')
            title = Utils.trans('you-declined-join-team', self.db_team.name)
            msg = Utils.trans('captain-not-response')
            embed = G5.bot.embed_template(title=title, description=msg)
            await G5.bot.send_dm(self.sender, embed)
            if self.sender in request_join_users:
                request_join_users.remove(self.sender)

        try:
            await self.delete()
        except Exception:
            pass


class RemoveTeamMessage(discord.Message):
    def __init__(self, message, db_team, user):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.db_team = db_team
        self.user = user
        self.future = None

    async def _process_request(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        if user != self.user:
            await self.remove_reaction(reaction.emoji, user)
            return

        if reaction.emoji not in ['✅', '❌']:
            await self.remove_reaction(reaction.emoji, user)
            return

        db_guild = await DB.Guild.get_guild_by_id(self.db_team.guild.id)
        self.db_team = await DB.Team.get_team_by_id(self.db_team.id)

        if reaction.emoji == '✅':
            if not self.db_team:
                msg = 'Team not found'
                await self._update_msg(msg)
                return

            db_lobby = await DB.Lobby.get_team_lobby(self.db_team.id)
            if db_lobby:
                msg = Utils.trans('cannot-delete-team-in-lobby',
                                  self.db_team.name, db_lobby.id)
                await self._update_msg(msg)
                return

            db_match = await DB.Match.get_team_match(self.db_team.id)
            if db_match:
                msg = Utils.trans('cannot-delete-team-in-match',
                                  self.db_team.name, db_match.id)
                await self._update_msg(msg)
                return

            await disband_team(self.db_team, db_guild)
            msg = Utils.trans('team-deleted', self.db_team.name)

        if reaction.emoji == '❌':
            msg = Utils.trans('team-not-deleted', self.db_team.name)

        await self._update_msg(msg)

    async def _update_msg(self, title):
        """"""
        embed = G5.bot.embed_template(title=title)
        try:
            await self.edit(embed=embed)
            await self.clear_reactions()
        except Exception:
            pass

        if self.future is not None:
            try:
                self.future.set_result(None)
            except asyncio.InvalidStateError:
                pass

    async def confirm(self):
        await self.add_reaction('✅')
        await self.add_reaction('❌')

        self.future = G5.bot.loop.create_future()
        G5.bot.add_listener(self._process_request, name='on_reaction_add')

        try:
            await asyncio.wait_for(self.future, 60)
        except asyncio.TimeoutError:
            G5.bot.remove_listener(
                self._process_request, name='on_reaction_add')


class TeamCog(commands.Cog):
    """"""

    async def setup_teams(self, guild):
        """"""
        db_guild = await DB.Guild.get_guild_by_id(guild.id)
        db_teams = await DB.Team.get_guild_teams(guild.id)
        awaitables = []

        for db_team in db_teams:
            awaitables.append(generate_team_msg(db_team, db_guild, False))
            if not db_team.role:
                team_role = guild.create_role(name='Team ' + db_team.name)
                await db_team.update({'role': team_role.id})

        if awaitables:
            asyncio.gather(*awaitables, return_exceptions=True)

    @commands.command(brief=Utils.trans('command-create-team-brief'),
                      usage='team-create <team_name>',
                      aliases=['team-create', 'create-team', 'createteam'])
    @DB.Guild.is_guild_setup()
    async def team_create(self, ctx, *args):
        """"""
        try:
            team_name = args[0]
        except IndexError:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        db_user = await DB.User.get_user_by_id(ctx.author.id, ctx.guild)
        db_team = await DB.Team.get_user_team(ctx.author.id, ctx.guild.id)

        if not db_user or not db_user.steam:
            raise commands.CommandInvokeError(
                Utils.trans('unable-create-team-not-linked'))

        if db_team:
            raise commands.CommandInvokeError(Utils.trans(
                'create-team-already-in-team', db_team.name))

        try:
            team_id = await API.Teams.create_team(db_guild.headers, team_name[:32], [db_user])
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

        team_role = await ctx.guild.create_role(name='Team ' + team_name[:32])

        await DB.Team.insert({
            'id': team_id,
            'guild': ctx.guild.id,
            'name': f"'{team_name[:32]}'",
            'captain': ctx.author.id,
            'flag': f"'{db_user.flag}'",
            'role': team_role.id
        })

        db_team = await DB.Team.get_team_by_id(team_id)
        await db_team.insert_user(ctx.author.id)
        await ctx.author.add_roles(team_role)

        msg = Utils.trans('team-create-success', db_team.name)
        embed = G5.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)

        await generate_team_msg(db_team, db_guild)

    @ commands.command(brief=Utils.trans('command-kick-team-brief'),
                       usage='team-kick <mention>',
                       aliases=['team-kick', 'kickteam', 'kick-team'])
    @ DB.Guild.is_guild_setup()
    async def team_kick(self, ctx):
        """"""
        try:
            target = ctx.message.mentions[0]
        except IndexError:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        if target == ctx.author:
            raise commands.CommandInvokeError(Utils.trans('cannot-kick-self'))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        db_team = await DB.Team.get_user_team(ctx.author.id, ctx.guild.id)

        if not db_team:
            raise commands.CommandInvokeError(Utils.trans('do-not-have-team'))

        if ctx.author != db_team.captain:
            raise commands.CommandInvokeError(
                Utils.trans('kick-teammate-not-creator'))

        team_users = await db_team.get_users()
        if target not in team_users:
            raise commands.CommandInvokeError(Utils.trans('kick-player-not-in-team',
                                                          target.display_name))

        db_lobby = await DB.Lobby.get_team_lobby(db_team.id)
        if db_lobby:
            raise commands.CommandInvokeError(Utils.trans(
                'cannot-kick-team-in-lobby', db_team.name, db_lobby.id))

        db_match = await DB.Match.get_team_match(db_team.id)
        if db_match:
            raise commands.CommandInvokeError(Utils.trans(
                'cannot-kick-team-in-match', db_team.name, db_match.id))

        target_db_user = await DB.User.get_user_by_id(target.id, db_team.guild)

        try:
            await API.Teams.remove_team_member(db_guild.headers, db_team.id, target_db_user.steam)
        except Exception as e:
            G5.bot.logger.info(str(e))

        await db_team.delete_users([target.id])

        try:
            await target.remove_roles(db_team.role)
        except Exception:
            pass

        msg = Utils.trans('you-kicked-from-team', db_team.name)
        embed = G5.bot.embed_template(title=msg)
        await G5.bot.send_dm(target, embed)

        msg = Utils.trans('teammate-kick-success',
                          target.display_name, db_team.name)
        embed = G5.bot.embed_template(title=msg)
        await ctx.reply(embed=embed)

        await generate_team_msg(db_team, db_guild)

    @ commands.command(brief=Utils.trans('command-delete-team-brief'),
                       aliases=['team-delete', 'deleteteam', 'delete-team'])
    @ DB.Guild.is_guild_setup()
    async def team_delete(self, ctx):
        """"""
        db_team = None
        mention_team_role = None

        try:
            mention_team_role = ctx.message.raw_role_mentions[0]
            if mention_team_role:
                if not ctx.author.guild_permissions.administrator:
                    raise commands.CommandInvokeError(
                        Utils.trans('no-perms-delete-other-team'))
                db_team = await DB.Team.get_team_by_role(mention_team_role)
                if not db_team:
                    raise commands.CommandInvokeError(
                        Utils.trans('team-not-found'))
        except IndexError:
            pass

        if not db_team:
            db_user = await DB.User.get_user_by_id(ctx.author.id, ctx.guild)
            if db_user and db_user.steam:
                db_team = await DB.Team.get_user_team(ctx.author.id, ctx.guild.id)

        if not db_team:
            raise commands.CommandInvokeError(Utils.trans('do-not-have-team'))

        if not mention_team_role and ctx.author != db_team.captain:
            raise commands.CommandInvokeError(
                Utils.trans('only-creator-remove-team'))

        msg = Utils.trans('confirm-remove-team', db_team.name)
        embed = G5.bot.embed_template(title=msg)
        remove_team_msg = await ctx.send(embed=embed)

        menu = RemoveTeamMessage(remove_team_msg, db_team, ctx.author)
        await menu.confirm()

    @ commands.Cog.listener()
    async def on_member_remove(self, user):
        """"""
        db_user = await DB.User.get_user_by_id(user.id, user.guild)
        if not db_user or not db_user.steam:
            return

        db_guild = await DB.Guild.get_guild_by_id(user.guild.id)
        db_team = await DB.Team.get_user_team(user.id, user.guild.id)
        if not db_team:
            return

        if db_team.captain is None:
            guild_lobbies = await DB.Lobby.get_guild_lobbies(user.guild)
            lobby_cog = G5.bot.get_cog('LobbyCog')
            title = Utils.trans('team-left-lobby', db_team.name)
            for lobby in guild_lobbies:
                if db_team.id == lobby.team1_id:
                    await lobby.update({'team1_id': 'NULL'})
                    await lobby_cog.update_queue_msg(lobby, title)
                elif db_team.id == lobby.team2_id:
                    await lobby.update({'team2_id': 'NULL'})
                    await lobby_cog.update_queue_msg(lobby, title)
            await disband_team(db_team, db_guild)
        else:
            await remove_team_member(db_team, db_user, db_guild)
