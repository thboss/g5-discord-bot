# match.py

from discord.ext import commands, tasks
import discord

from ..utils import Utils, API, DB
from ..menus import PickTeams, MapVeto, Embeds
from ..resources import G5

from random import shuffle
from asyncpg.exceptions import UniqueViolationError
import traceback
import asyncio


class MatchCog(commands.Cog):
    """"""

    @ commands.command(usage='end <match_id> [OPTIONAL winner: team1|team2]',
                       brief=Utils.trans('command-end-brief'),
                       aliases=['stop', 'cancel', 'forfeit'])
    @ commands.has_permissions(kick_members=True)
    @ DB.Guild.is_guild_setup()
    async def end(self, ctx, match_id=None, winner=None):
        """"""
        try:
            match_id = int(match_id)
        except (TypeError, ValueError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        if winner and winner not in ['team1', 'team2']:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        try:
            api_match = await API.Matches.get_stats(match_id)
            await api_match.cancel(db_guild.headers, winner[4] if winner else None)
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

        title = Utils.trans('command-end-success', match_id)
        embed = G5.bot.embed_template(title=title)
        await ctx.send(embed=embed)

    @ commands.command(usage='adduser <match_id> <team1|team2|spec> <mention>',
                       brief=Utils.trans('command-add-brief'),
                       aliases=['add-user', 'add-player'])
    @ commands.has_permissions(kick_members=True)
    @ DB.Guild.is_guild_setup()
    async def add_user(self, ctx, match_id=None, team=None):
        """"""
        if team not in ['team1', 'team2', 'spec']:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        try:
            match_id = int(match_id)
            user = ctx.message.mentions[0]
        except (TypeError, ValueError, IndexError):
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_user = await DB.User.get_user_by_id(user.id, ctx.guild)
        if not db_user or not db_user.steam:
            raise commands.CommandInvokeError(Utils.trans(
                'command-add-not-linked', user.mention))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        db_match = await DB.Match.get_match_by_id(match_id)
        if not db_match:
            raise commands.CommandInvokeError(Utils.trans('match-not-found'))

        db_lobby = await DB.Lobby.get_lobby_by_id(db_match.lobby_id, ctx.guild.id)

        try:
            await db_match.insert_user(user.id)
            api_match = await API.Matches.get_stats(match_id)
            await api_match.add_player(
                db_guild.headers,
                db_user.steam,
                user.display_name,
                team
            )
        except UniqueViolationError:
            raise commands.CommandInvokeError(Utils.trans(
                'user-already-in-match', user.display_name))
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

        if db_lobby and db_lobby.pug:
            await user.remove_roles(db_guild.linked_role)

        try:
            if team == 'team1':
                await db_match.team1_channel.set_permissions(user, connect=True)
                await user.move_to(db_match.team1_channel)
            elif team == 'team2':
                await db_match.team2_channel.set_permissions(user, connect=True)
                await user.move_to(db_match.team2_channel)
            else:
                await db_match.team1_channel.set_permissions(user, connect=True)
                await db_match.team2_channel.set_permissions(user, connect=True)
        except Exception as e:
            G5.bot.logger.info(str(e))

        msg = Utils.trans('command-add-success', user.mention, match_id)
        embed = G5.bot.embed_template(description=msg)
        await ctx.send(embed=embed)

    @ commands.command(usage='removeuser <match_id> <mention>',
                       brief=Utils.trans('command-remove-brief'),
                       aliases=['remove-user', 'remove-player'])
    @ commands.has_permissions(kick_members=True)
    @ DB.Guild.is_guild_setup()
    async def remove_user(self, ctx, match_id=None):
        """"""
        try:
            match_id = int(match_id)
            user = ctx.message.mentions[0]
        except:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_user = await DB.User.get_user_by_id(user.id, ctx.guild)
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        db_match = await DB.Match.get_match_by_id(match_id)

        if not db_user or not db_user.steam:
            raise commands.CommandInvokeError(Utils.trans(
                'command-add-not-linked', user.mention))

        try:
            api_match = await API.Matches.get_stats(match_id)
            await api_match.remove_player(db_guild.headers, db_user.steam)
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

        await db_match.delete_user(user.id)
        await user.add_roles(db_guild.linked_role)
        try:
            await db_match.team1_channel.set_permissions(user, connect=False)
            await db_match.team2_channel.set_permissions(user, connect=False)
            await user.move_to(db_guild.prematch_channel)
        except Exception:
            pass

        msg = Utils.trans('command-remove-success', user.mention, match_id)
        embed = G5.bot.embed_template(description=msg)
        await ctx.send(embed=embed)

    @ commands.command(usage='replaceuser <mention> <mention>',
                       brief='Replace match player',
                       aliases=['replace-user', 'replace-player'])
    @ commands.has_permissions(kick_members=True)
    @ DB.Guild.is_guild_setup()
    async def replace_user(self, ctx):
        """"""
        try:
            curr_user = ctx.message.mentions[0]
            new_user = ctx.message.mentions[1]
            if curr_user == new_user:
                raise
        except:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_match = await DB.Match.get_user_match(curr_user.id, ctx.guild.id)
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        curr_db_user = await DB.User.get_user_by_id(curr_user.id, ctx.guild)
        new_db_user = await DB.User.get_user_by_id(new_user.id, ctx.guild)

        if not db_match:
            raise commands.CommandInvokeError(Utils.trans(
                'player-not-in-match', curr_user.display_name))

        if not new_db_user or not new_db_user.steam:
            raise commands.CommandInvokeError(Utils.trans(
                'user-not-linked', new_user.display_name))

        try:
            api_match = await API.Matches.get_stats(db_match.id)
            api_team = await API.Teams.get_team(db_match.team1_id)
            await api_match.remove_player(db_guild.headers, curr_db_user.steam)
            if curr_db_user.steam in api_team.auth_name:
                str_team = 'team1'
                channel = db_match.team1_channel
            else:
                str_team = 'team2'
                channel = db_match.team2_channel
            await api_match.add_player(
                db_guild.headers,
                new_db_user.steam,
                new_user.display_name,
                str_team
            )
            await db_match.delete_user(curr_user.id)
            await db_match.insert_user(new_user.id)
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

        if channel:
            awaitables = [
                channel.set_permissions(new_user, connect=True),
                channel.set_permissions(curr_user, connect=False),
                new_user.remove_roles(db_guild.linked_role),
                curr_user.add_roles(db_guild.linked_role),
                curr_user.move_to(db_guild.prematch_channel)
            ]
            await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)

        title = Utils.trans('player-match-replaced',
                            curr_user.display_name, new_user.display_name, db_match.id)
        embed = G5.bot.embed_template(title=title)
        await ctx.send(embed=embed)

    @ commands.command(usage='pause <match_id>',
                       brief=Utils.trans('command-pause-brief'))
    @ commands.has_permissions(kick_members=True)
    @ DB.Guild.is_guild_setup()
    async def pause(self, ctx, match_id=None):
        """"""
        if not match_id:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)

        try:
            api_match = await API.Matches.get_stats(match_id)
            await api_match.pause(db_guild.headers)
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

        msg = Utils.trans('command-pause-success', match_id)
        embed = G5.bot.embed_template(description=msg)
        await ctx.send(embed=embed)

    @ commands.command(usage='unpause <match_id>',
                       brief=Utils.trans('command-unpause-brief'))
    @ commands.has_permissions(kick_members=True)
    @ DB.Guild.is_guild_setup()
    async def unpause(self, ctx, match_id=None):
        """"""
        if not match_id:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)

        try:
            api_match = await API.Matches.get_stats(match_id)
            await api_match.unpause(db_guild.headers)
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

        msg = Utils.trans('command-unpause-success', match_id)
        embed = G5.bot.embed_template(description=msg)
        await ctx.send(embed=embed)

    async def autobalance_teams(self, db_guild, users):
        """ Balance teams based on players' avarage raitng. """
        # Get players and sort by average rating
        _users = await DB.User.get_users(users, db_guild.guild)
        try:
            leaderboard = await API.PlayerStats.get_leaderboard(_users)
        except Exception as e:
            G5.bot.logger.info(str(e))
            return self.randomize_teams(users)

        stats_dict = dict(zip(leaderboard, users))
        players = list(stats_dict.keys())
        players.sort(key=lambda x: x.elo)

        # Balance teams
        team_size = len(players) // 2
        team1_users = [players.pop()]
        team2_users = [players.pop()]

        while players:
            if len(team1_users) >= team_size:
                team2_users.append(players.pop())
            elif len(team2_users) >= team_size:
                team1_users.append(players.pop())
            elif sum(p.elo for p in team1_users) < sum(p.elo for p in team2_users):
                team1_users.append(players.pop())
            else:
                team2_users.append(players.pop())

        team1_users = list(map(stats_dict.get, team1_users))
        team2_users = list(map(stats_dict.get, team2_users))
        return team1_users, team2_users

    async def draft_teams(self, db_guild, message, users, db_lobby):
        """"""
        menu = PickTeams(message, users, db_lobby)
        teams = await menu.draft(db_guild)
        return teams[0], teams[1]

    def randomize_teams(self, users):
        """"""
        temp_users = users.copy()
        shuffle(temp_users)
        team_size = len(temp_users) // 2
        team1_users = temp_users[:team_size]
        team2_users = temp_users[team_size:]
        return team1_users, team2_users

    async def update_setup_msg(self, message, desc, title=Utils.trans('match-setup-process')):
        """"""
        embed = G5.bot.embed_template(title=title, description=desc)
        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            pass
        await asyncio.sleep(2)

    async def start_match(self, users, db_lobby, db_guild, message):
        """"""
        description = 'Match Setup Process..'
        team1_id = 0
        team2_id = 0
        team1_name = None
        team2_name = None
        team1_users = None
        team2_users = None
        season_id = None
        try:
            if not db_lobby.pug:
                db_team1 = await DB.Team.get_team_by_id(db_lobby.team1_id)
                db_team2 = await DB.Team.get_team_by_id(db_lobby.team2_id)
                team1_name = db_team1.name
                team2_name = db_team2.name
                team1_id = db_team1.id
                team2_id = db_team2.id
                await API.Teams.get_team(team1_id)
                await API.Teams.get_team(team2_id)
                team1_users = await db_team1.get_users()
                team2_users = await db_team2.get_users()
                if db_team1.captain in team1_users:
                    team1_users.insert(0, team1_users.pop(
                        team1_users.index(db_team1.captain)))
                if db_team2.captain in team2_users:
                    team2_users.insert(0, team2_users.pop(
                        team2_users.index(db_team2.captain)))

            else:
                if db_lobby.team_method == 'captains' and len(users) > 3:
                    team1_users, team2_users = await self.draft_teams(db_guild, message, users, db_lobby)
                elif db_lobby.team_method == 'autobalance' and len(users) > 3:
                    team1_users, team2_users = await self.autobalance_teams(db_guild, users)
                else:  # team_method is random
                    team1_users, team2_users = self.randomize_teams(users)

            description = '⌛️ 1. ' + Utils.trans('creating-teams')
            await self.update_setup_msg(message, description)

            if db_lobby.pug:
                team1_db_users = await DB.User.get_users(team1_users, db_guild.guild)
                team2_db_users = await DB.User.get_users(team2_users, db_guild.guild)
                team1_name = team1_users[0].display_name
                team2_name = team2_users[0].display_name
                team1_id = await API.Teams.create_team(db_guild.headers, team1_name, team1_db_users)
                team2_id = await API.Teams.create_team(db_guild.headers, team2_name, team2_db_users)

            description = description.replace('⌛️', '✅')
            description += '\n⌛️ 2. ' + Utils.trans('pick-maps')
            await self.update_setup_msg(message, description)

            mpool = await db_lobby.get_maps()
            veto_menu = MapVeto(
                message, db_lobby.series, mpool[:18])
            maps_list = await veto_menu.veto(team1_users[0], team2_users[0])

            description = description.replace('⌛️', '✅')
            description += '\n⌛️ 3. ' + Utils.trans('find-servers')
            await self.update_setup_msg(message, description)

            match_server = await self.find_match_server(db_guild, db_lobby.region)

            if db_lobby.season_id:
                await API.Seasons.get_season(db_lobby.season_id)
                season_id = db_lobby.season_id

            description = description.replace('⌛️', '✅')
            description += '\n⌛️ 4. ' + Utils.trans('creating-match')
            await self.update_setup_msg(message, description)

            str_maps = ' '.join(m.dev_name for m in maps_list)
            cvars = await db_lobby.get_cvars()
            match_id = await API.Matches.create(
                db_guild.headers,
                match_server.id,
                team1_id,
                team2_id,
                season_id,
                str_maps,
                len(team1_users + team2_users),
                db_lobby.pug,
                cvars=cvars
            )

            description = description.replace('⌛️', '✅')
            await self.update_setup_msg(message, description)

        except asyncio.TimeoutError:
            description = Utils.trans('match-took-too-long')
        except (discord.NotFound, ValueError):
            description = Utils.trans('match-setup-cancelled')
        except Exception as e:
            G5.bot.logger.info(str(e))
            description = description.replace('⌛️', '❌')
            description += f'\n\n```{e}```'
        else:
            match_catg, team1_channel, team2_channel = await self.prepare_match_channels(
                match_id,
                team1_name,
                team2_name,
                team1_users,
                team2_users,
                db_guild
            )

            db_match = await DB.Match.insert_match({
                'id': match_id,
                'lobby': db_lobby.id,
                'guild': db_guild.guild.id,
                'message': message.id,
                'category': match_catg.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id,
                'team1_id': team1_id,
                'team2_id': team2_id
            })

            await db_match.insert_users([user.id for user in team1_users + team2_users])
            api_match = await API.Matches.get_stats(match_id)
            game_server = await API.Servers.get_server(db_guild.headers, match_server.id)
            embed = Embeds.match_info(api_match, game_server)

            try:
                await message.edit(embed=embed)
            except discord.NotFound:
                try:
                    await db_lobby.queue_channel.send(embed=embed)
                except Exception as e:
                    G5.bot.logger.info(str(e))

            if not self.check_live_matches.is_running():
                self.check_live_matches.start()

            return True

        # Delete the created teams from API if setup didn't complete
        if db_lobby.pug:
            try:
                if team1_id:
                    await API.Teams.delete_team(db_guild.headers, team1_id)
            except Exception as e:
                G5.bot.logger.info(str(e))
            try:
                if team2_id:
                    await API.Teams.delete_team(db_guild.headers, team2_id)
            except Exception as e:
                G5.bot.logger.info(str(e))

        await self.update_setup_msg(message, description, title=Utils.trans('match-setup-failed'))
        Utils.clear_messages([message])

        return False

    async def find_match_server(self, db_guild, region):
        """"""
        try:
            servers = await API.Servers.get_servers(db_guild.headers)
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise Exception(str(e))

        for server in servers:
            if server.in_use or (region and server.flag != region):
                continue

            try:
                await API.Servers.is_server_available(db_guild.headers, server.id)
            except Exception as e:
                G5.bot.logger.info(str(e))
                continue
            return server

        raise Exception(Utils.trans('no-game-servers'))

    async def prepare_match_channels(
        self,
        match_id,
        team1_name,
        team2_name,
        team1_users,
        team2_users,
        db_guild
    ):
        """"""
        match_catg = await db_guild.guild.create_category_channel(Utils.trans("match-id", match_id))

        team1_channel = await db_guild.guild.create_voice_channel(
            name=Utils.trans("match-team", team1_name),
            category=match_catg
        )

        team2_channel = await db_guild.guild.create_voice_channel(
            name=Utils.trans("match-team", team2_name),
            category=match_catg
        )

        awaitables = [
            team1_channel.set_permissions(
                db_guild.guild.self_role, connect=True),
            team2_channel.set_permissions(
                db_guild.guild.self_role, connect=True),
            team1_channel.set_permissions(
                db_guild.guild.default_role, connect=False, read_messages=True),
            team2_channel.set_permissions(
                db_guild.guild.default_role, connect=False, read_messages=True)
        ]

        for user in team1_users:
            awaitables.append(
                team1_channel.set_permissions(user, connect=True))
            awaitables.append(user.move_to(team1_channel))

        for user in team2_users:
            awaitables.append(
                team2_channel.set_permissions(user, connect=True))
            awaitables.append(user.move_to(team2_channel))

        await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)
        return match_catg, team1_channel, team2_channel

    async def finalize_match(self, db_match, db_guild, db_lobby):
        """"""
        match_players = await db_match.get_users()

        awaitables = []
        for user in match_players:
            if user is not None:
                awaitables.append(user.move_to(db_guild.prematch_channel))
                if db_lobby and db_lobby.pug:
                    awaitables.append(user.add_roles(db_guild.linked_role))

        if db_lobby and not db_lobby.pug:
            team1 = await DB.Team.get_team_by_id(db_match.team1_id)
            team2 = await DB.Team.get_team_by_id(db_match.team2_id)
            if team1:
                awaitables.append(db_lobby.lobby_channel.set_permissions(
                    team1.role, overwrite=None))
            if team2:
                awaitables.append(db_lobby.lobby_channel.set_permissions(
                    team2.role, overwrite=None))

        await asyncio.gather(*awaitables, loop=G5.bot.loop, return_exceptions=True)

        for channel in [db_match.team1_channel, db_match.team2_channel, db_match.category]:
            try:
                await channel.delete()
            except (AttributeError, discord.NotFound):
                pass

        await db_match.delete_match()

    @ tasks.loop(seconds=20.0)
    async def check_live_matches(self):
        """"""
        db_matches = await DB.Match.get_all_matches()
        if not db_matches:
            self.check_live_matches.cancel()

        for db_match in db_matches:
            try:
                await self.update_match_stats(db_match)
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__)
                G5.bot.logger.error(
                    f'Uncaught exception when handling update_match_stats({db_match.id}): {e}')

    async def update_match_stats(self, db_match):
        """"""
        mapstats = []
        game_server = None
        message = None
        db_guild = await DB.Guild.get_guild_by_id(db_match.guild.id)
        db_lobby = await DB.Lobby.get_lobby_by_id(db_match.lobby_id, db_match.guild.id)
        try:
            message = await db_lobby.queue_channel.fetch_message(db_match.message_id)
        except (AttributeError, discord.NotFound):
            pass

        try:
            api_match = await API.Matches.get_stats(db_match.id)
        except Exception as e:
            G5.bot.logger.info(str(e))
            if 'No match found' in str(e):
                await self.finalize_match(db_match, db_guild, db_lobby)
            return

        try:
            game_server = await API.Servers.get_server(db_guild.headers, api_match.server_id)
        except Exception as e:
            G5.bot.logger.info(str(e))

        try:
            mapstats = await API.MapStats.get_mapstats(db_match.id)
        except Exception as e:
            G5.bot.logger.info(str(e))

        try:
            embed = Embeds.match_info(api_match, game_server, mapstats)
            await message.edit(embed=embed)
        except (AttributeError, discord.NotFound):
            pass

        if not api_match.end_time and not api_match.cancelled and not api_match.forfeit:
            return

        try:
            await message.delete()
        except (AttributeError, discord.NotFound):
            pass

        if mapstats and not api_match.cancelled:
            try:
                embed = Embeds.match_info(api_match, mapstats=mapstats)
                await db_guild.results_channel.send(embed=embed)
            except Exception as e:
                G5.bot.logger.info(str(e))

        await self.finalize_match(db_match, db_guild, db_lobby)
