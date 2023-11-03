import logging
from aiohttp import web
from bot.helpers.api import Match
from bot.helpers.configs import Config

from bot.helpers.db import db


class WebServer:
    def __init__(self, bot):
        self.logger = logging.getLogger("API")
        self.host = Config.webserver_host
        self.port = Config.webserver_port
        self.bot = bot

    async def match_end(self, req):
        authorization = req.headers.get('Authorization').strip('Bearer ')
        match_model = await db.get_match_by_api_key(authorization, self.bot)
        guild_model = await db.get_guild_by_id(match_model.guild.id, self.bot)
        if not match_model or not guild_model:
            return

        resp_data = await req.json()
        match_api = Match.from_dict(resp_data)
        match_cog = self.bot.get_cog("Match")
        await match_cog.update_match_stats(match_model, guild_model, match_api)
        self.logger.info(f"Received webhook data from {req.url}")

    async def round_end(self, req):
        authorization = req.headers.get('Authorization').strip('Bearer ')
        match_model = await db.get_match_by_api_key(authorization, self.bot)
        guild_model = await db.get_guild_by_id(match_model.guild.id, self.bot)
        if not match_model or not guild_model:
            return

        resp_data = await req.json()
        match_api = Match.from_dict(resp_data)
        match_cog = self.bot.get_cog("Match")
        await match_cog.update_match_stats(match_model, guild_model, match_api)
        self.logger.info(f"Received webhook data from {req.url}")

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
