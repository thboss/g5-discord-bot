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
                await self._playerstats(ctx, db_user, pug=False, season_id=season.id)
                await self._playerstats(ctx, db_user, pug=True, season_id=season.id)
        except Exception as e:
            G5.bot.logger.info(str(e))

        await self._playerstats(ctx, db_user, pug=True)
        await self._playerstats(ctx, db_user, pug=False)

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
                    await self._leaderboard(leaders_channel, users, pug=True, season_id=season.id)
            except Exception as e:
                G5.bot.logger.info(str(e))

            await self._leaderboard(leaders_channel, users, pug=True)
            await self._leaderboard(leaders_channel, users, pug=False)

    async def _playerstats(self, ctx, db_user, pug=False, season_id=None):
        """"""
        try:
            stats = await API.PlayerStats.get_player_stats(db_user, pug=pug, season_id=season_id)
            file = Utils.generate_statistics_img(stats)
            await ctx.send(file=file)
        except Exception as e:
            G5.bot.logger.info(str(e))

    async def _leaderboard(self, channel, users, pug=False, season_id=None):
        """"""
        try:
            players = await API.PlayerStats.get_leaderboard(users, pug=pug, season_id=season_id)
            players.sort(key=lambda u: u.rating, reverse=True)
            if players:
                file = Utils.generate_leaderboard_img(players[:10])
                await channel.send(file=file)
        except Exception as e:
            G5.bot.logger.info(str(e))