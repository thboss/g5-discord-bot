# stats.py

from discord.ext import commands, tasks

from ..utils import Utils, API, DB
from ..resources import G5


class StatsCog(commands.Cog):
    """"""

    @commands.command(brief=Utils.trans('command-stats-brief'),
                      aliases=['rank'])
    @DB.Guild.is_guild_setup()
    async def stats(self, ctx):
        """"""
        db_user = await DB.User.get_user_by_id(ctx.author.id, ctx.guild)
        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        if not db_user or not db_user.steam:
            raise commands.CommandInvokeError(Utils.trans(
                'stats-not-linked', ctx.author.display_name))

        try:
            seasons = await API.Seasons.my_seasons(db_guild.headers)
            for season in seasons:
                stats = await API.PlayerStats.get_player_stats(db_user, season_id=season.id)
                if stats:
                    file = Utils.generate_statistics_img(stats, season)
                    await ctx.send(file=file)
        except Exception as e:
            G5.bot.logger.info(str(e))

        try:
            stats = await API.PlayerStats.get_player_stats(db_user)
            file = Utils.generate_statistics_img(stats)
            await ctx.send(file=file)
        except Exception as e:
            G5.bot.logger.info(str(e))
            raise commands.CommandInvokeError(str(e))

    @ tasks.loop(seconds=300.0)
    async def update_leaderboard(self):
        """"""
        for guild in G5.bot.guilds:
            db_guild = await DB.Guild.get_guild_by_id(guild.id)
            users = await DB.User.get_users(guild.members, guild)
            if not users:
                continue

            leaders_channel = db_guild.leaders_channel
            if not leaders_channel:
                continue

            try:
                await leaders_channel.purge()
            except Exception:
                pass

            try:
                seasons = await API.Seasons.my_seasons(db_guild.headers)
                for season in seasons:
                    season_players = await API.PlayerStats.get_leaderboard(users, season_id=season.id)
                    season_players.sort(key=lambda u: u.score, reverse=True)
                    if season_players:
                        file = Utils.generate_leaderboard_img(
                            season_players[:10], season)
                        await leaders_channel.send(file=file)
            except Exception as e:
                G5.bot.logger.info(str(e))

            try:
                players = await API.PlayerStats.get_leaderboard(users)
                players.sort(key=lambda u: u.score, reverse=True)
                if players:
                    file = Utils.generate_leaderboard_img(players[:10])
                    await leaders_channel.send(file=file)
            except Exception as e:
                G5.bot.logger.info(str(e))
