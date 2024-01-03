import logging
from aiohttp import web

from bot.helpers.api import Match
from bot.resources import Config
from bot.helpers.utils import generate_leaderboard_img, generate_scoreboard_img


class WebServer:
    _instance = None  # Class variable to store the single instance

    def __new__(cls, bot):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, bot):
        if getattr(self, 'initialized', False):
            return
        self.initialized = True  # Ensure initialization only once
        self.server_running = False
        self.bot = bot
        self.logger = logging.getLogger("API")
        self.host = Config.webserver_host
        self.port = Config.webserver_port
        self.match_cog = self.bot.get_cog("Match")

    async def match_end(self, req):
        self.logger.info(f"Received webhook data from {req.url}")
        api_key = req.headers.get('Authorization').strip('Bearer ')
        match_model = await self.bot.db.get_match_by_api_key(api_key, self.bot)
        guild_model = await self.bot.db.get_guild_by_id(match_model.guild.id, self.bot)
        if not match_model or not guild_model:
            return

        try:
            await self.bot.api.stop_game_server(match_model.game_server_id, guild_model.dathost_auth)
        except:
            pass

        resp_data = await req.json()
        match_api = Match.from_dict(resp_data)
        team1_stats = match_api.team1_players
        team2_stats = match_api.team2_players

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
            await message.delete()
        except:
            pass
        
        if not match_api.cancel_reason:
            await self._release_match_stats(guild_model, match_api, team1_stats, team2_stats)
            await self._update_players_stats(team1_stats, team2_stats)
            await self._update_leaderboard(guild_model)

        await self.match_cog.finalize_match(match_model, guild_model)


    async def round_end(self, req):
        self.logger.debug(f"Received webhook data from {req.url}")
        game_server = None
        message = None
        authorization = req.headers.get('Authorization').strip('Bearer ')
        match_model = await self.bot.db.get_match_by_api_key(authorization, self.bot)
        guild_model = await self.bot.db.get_guild_by_id(match_model.guild.id, self.bot)
        if not match_model or not guild_model:
            return

        resp_data = await req.json()
        match_api = Match.from_dict(resp_data)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
        except:
            pass

        try:
            game_server = await self.bot.api.get_game_server(match_api.game_server_id, auth=guild_model.dathost_auth)
        except:
            pass

        if message:
            try:
                embed = self.match_cog.embed_match_info(match_api, game_server)
                team1_users = await self.bot.db.get_match_users(match_api.id, match_model.guild, team='team1')
                team2_users = await self.bot.db.get_match_users(match_api.id, match_model.guild, team='team2')
                self.match_cog.add_teams_fields(embed, team1_users, team2_users)
                await message.edit(embed=embed)
            except Exception as e:
                self.logger.error(e, exc_info=1)


    async def _update_leaderboard(self, guild_model):
        """"""
        leaderboard_channel = guild_model.leaderboard_channel
        if not leaderboard_channel:
            return

        try:
            await leaderboard_channel.purge()
        except:
            pass
        
        try:
            leaderboard = await self.bot.db.get_players(guild_model.guild.members)
            leaderboard.sort(key=lambda u: u.elo, reverse=True)
            leaderboard = list(filter(lambda u: u.played_matches != 0, leaderboard))
            if leaderboard:
                try:
                    file = generate_leaderboard_img(leaderboard[:10])
                    await leaderboard_channel.send(file=file)
                except Exception as e:
                    self.bot.logger.error(e, exc_info=1)
        except:
            pass

    async def _update_players_stats(self, team1_stats, team2_stats):
        for player_stat in team1_stats + team2_stats:
            try:
                player_model = await self.bot.db.get_player_by_steam_id(player_stat.steam_id, self.bot)
                if player_model:
                    await self.bot.db.update_player_stats(player_model.discord.id, player_stat)
            except Exception as e:
                self.logger.error(e, exc_info=1)

    async def _release_match_stats(self, guild_model, match_api, team1_stats, team2_stats):
        try:
            for p in team1_stats:
                player_model = await self.bot.db.get_player_by_steam_id(p.steam_id, self.bot)
                p.member = player_model.discord
            for p in team2_stats:
                player_model = await self.bot.db.get_player_by_steam_id(p.steam_id, self.bot)
                p.member = player_model.discord
            team1_stats.sort(key=lambda x: x.score, reverse=True)
            team2_stats.sort(key=lambda x: x.score, reverse=True)
            file = generate_scoreboard_img(match_api, team1_stats[:6], team2_stats[:6])
            await guild_model.results_channel.send(file=file)
        except Exception as e:
            self.logger.error(e, exc_info=1)

    async def start_webhook_server(self):
        if self.server_running:
            self.logger.warning("Webhook server is already running.")
            return

        self.logger.info(f'Starting webhook server on {self.host}:{self.port}')

        app = web.Application()

        app.router.add_post("/cs2bot-api/match-end", self.match_end)
        app.router.add_post("/cs2bot-api/round-end", self.round_end)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, host=self.host, port=self.port)

        try:
            await site.start()
            self.server_running = True
            self.logger.info("Webhook server started and running in the background")
        except Exception as e:
            self.logger.error("Failed to start the webhook server.", e, exc_info=1)
            self.server_running = False
