import logging
from aiohttp import web
from bot.helpers.api import api, Match
from bot.helpers.configs import Config

from bot.helpers.db import db
from bot.helpers.utils import generate_scoreboard_img


class WebServer:
    def __init__(self, bot):
        self.logger = logging.getLogger("API")
        self.host = Config.webserver_host
        self.port = Config.webserver_port
        self.bot = bot
        self.match_cog = bot.get_cog("Match")

    async def match_end(self, req):
        message = None
        api_key = req.headers.get('Authorization').strip('Bearer ')
        match_model = await db.get_match_by_api_key(api_key, self.bot)
        guild_model = await db.get_guild_by_id(match_model.guild.id, self.bot)
        if not match_model or not guild_model:
            return

        try:
            await api.stop_game_server(match_model.game_server_id, guild_model.dathost_auth)
        except:
            pass

        resp_data = await req.json()
        match_api = Match.from_dict(resp_data)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
            await message.delete()
        except:
            pass


        team1_stats = match_api.team1_players
        team2_stats = match_api.team2_players
        
        # Release match stats
        try:
            for p in team1_stats:
                user_model = await db.get_user_by_steam_id(p.steam_id, self.bot)
                p.member = user_model.member
            for p in team2_stats:
                user_model = await db.get_user_by_steam_id(p.steam_id, self.bot)
                p.member = user_model.member
            team1_stats.sort(key=lambda x: x.score, reverse=True)
            team2_stats.sort(key=lambda x: x.score, reverse=True)
            file = generate_scoreboard_img(match_api, team1_stats[:6], team2_stats[:6])
            await guild_model.results_channel.send(file=file)
        except Exception as e:
            self.logger.error(e, exc_info=1)

        if not match_api.cancel_reason:
            # Update players stats
            for player_stat in team1_stats + team2_stats:
                try:
                    user_model = await db.get_user_by_steam_id(player_stat.steam_id, self.bot)
                    if user_model:
                        await db.update_user_stats(user_model.member.id, player_stat)
                except Exception as e:
                    self.logger.error(e, exc_info=1)

        await self.match_cog.finalize_match(match_model, guild_model)

        self.logger.info(f"Received webhook data from {req.url}")

    async def round_end(self, req):
        game_server = None
        message = None
        authorization = req.headers.get('Authorization').strip('Bearer ')
        match_model = await db.get_match_by_api_key(authorization, self.bot)
        guild_model = await db.get_guild_by_id(match_model.guild.id, self.bot)
        if not match_model or not guild_model:
            return

        resp_data = await req.json()
        match_api = Match.from_dict(resp_data)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
        except:
            pass

        try:
            game_server = await api.get_game_server(match_api.game_server_id, auth=guild_model.dathost_auth)
        except:
            pass

        if message:
            try:
                embed = self.match_cog.embed_match_info(match_api, game_server)
                team1_users = await db.get_match_users(match_api.id, match_model.guild, team='team1')
                team2_users = await db.get_match_users(match_api.id, match_model.guild, team='team2')
                self.add_teams_fields(embed, team1_users, team2_users)
                await message.edit(embed=embed)
            except Exception as e:
                self.logger.error(e, exc_info=1)

        self.logger.debug(f"Received webhook data from {req.url}")

    async def start_webhook_server(self):
        self.logger.info(f'Starting webhook server on {self.host}:{self.port}')

        app = web.Application()

        app.router.add_post("/cs2bot-api/match-end", self.match_end)
        app.router.add_post("/cs2bot-api/round-end", self.round_end)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, host=self.host, port=self.port)
        await site.start()

        self.logger.info("Webhook server started and running in the background")
