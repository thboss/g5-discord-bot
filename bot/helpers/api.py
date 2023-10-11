# bot/helpers/api.py

import asyncio
import logging
import json
import aiohttp
from typing import Literal, Optional, List
from bot.helpers.configs import Config
from bot.helpers.errors import APIError


class MatchPlayer:
    def __init__(self, data):
        self.match_id = data['match_id']
        self.steam_id = data['steam_id_64']
        self.team = data['team']
        self.connected = data['connected']
        self.kicked = data['kicked']
        self.kills = data['stats']['kills']
        self.assists = data['stats']['assists']
        self.deaths = data['stats']['deaths']
        self.mvps = data['stats']['mvps']
        self.score = data['stats']['score']

    @classmethod
    def from_dict(cls, data: dict) -> "MatchPlayer":
        return cls(data)


class Match:
    """"""

    def __init__(self, match_data: dict) -> None:
        """"""
        self.id = match_data['id']
        self.game_server_id = match_data['game_server_id']
        self.team1_name = match_data['team1']['name']
        self.team2_name = match_data['team2']['name']
        self.team1_score = match_data['team1']['stats']['score']
        self.team2_score = match_data['team2']['stats']['score']
        self.cancel_reason = match_data['cancel_reason']
        self.finished = match_data['finished']
        self.connect_time = match_data['settings']['connect_time']
        self.map = match_data['settings']['map']
        self.rounds_played = match_data['rounds_played']
        self.team1_players = [MatchPlayer.from_dict(player) for player in match_data['players'] if player['team'] == 'team1']
        self.team2_players = [MatchPlayer.from_dict(player) for player in match_data['players'] if player['team'] == 'team2']

    @classmethod
    def from_dict(cls, data: dict) -> "Match":
        return cls(data)

class GameServer:
    """"""

    def __init__(self, data: dict) -> None:
        """"""
        self.id = data['id']
        self.name = data['name']
        self.ip = data['ip']
        self.port = data['ports']['game']
        self.gotv_port = data['ports']['gotv']
        self.on = data['on']
        self.game_mode = data['cs2_settings']['game_mode']

    @classmethod
    def from_dict(cls, data: dict) -> "GameServer":
        return cls(data)


async def start_request_log(session, ctx, params):
    """"""
    ctx.start = asyncio.get_event_loop().time()
    logger = logging.getLogger('API')
    logger.debug(f'Sending {params.method} request to {params.url}')


async def end_request_log(session, ctx, params):
    """"""
    logger = logging.getLogger('API')
    elapsed = asyncio.get_event_loop().time() - ctx.start
    logger.debug(f'Response received from {params.url} ({elapsed:.2f}s)\n'
                f'    Status: {params.response.status}\n'
                f'    Reason: {params.response.reason}')
    try:
        resp_json = await params.response.json()
        logger.debug(f'Response JSON from {params.url}: {resp_json}')
    except Exception as e:
        pass

TRACE_CONFIG = aiohttp.TraceConfig()
TRACE_CONFIG.on_request_start.append(start_request_log)
TRACE_CONFIG.on_request_end.append(end_request_log)


class APIManager:
    """ Class to contain API request wrapper functions. """

    def __init__(self):
        self.logger = logging.getLogger("API")

    def connect(self, loop):
        self.logger.info('Starting API helper client session')
        self.session = aiohttp.ClientSession(
            base_url="https://dathost.net",
            auth= aiohttp.BasicAuth(Config.dathost_email, Config.dathost_password),
            loop=loop,
            json_serialize=lambda x: json.dumps(x, ensure_ascii=False),
            timeout=aiohttp.ClientTimeout(total=30),
            trace_configs=[TRACE_CONFIG] if Config.debug else None
        )

    async def close(self):
        """ Close the API helper's session. """
        self.logger.info('Closing API helper client session')
        await self.session.close()

    async def get_game_server(self, game_server_id: str) -> List[GameServer]:
        """"""
        url = f"/api/0.1/game-servers/{game_server_id}"

        try:
            async with self.session.get(url=url) as resp:
                resp_data = await resp.json()
                if not resp.ok:
                    raise ValueError(resp_data)
                return GameServer.from_dict(resp_data)
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError
        

    async def get_game_servers(self) -> List[GameServer]:
        """"""
        url = f"/api/0.1/game-servers"

        try:
            async with self.session.get(url=url) as resp:
                resp_data = await resp.json()
                return [GameServer.from_dict(game_server) for game_server in resp_data]
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError

    async def stop_game_server(self, server_id: str):
        """"""
        url = f"/api/0.1/game-servers/{server_id}/stop"

        try:
            async with self.session.post(url=url) as resp:
                await resp.json()
                return resp.ok
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError
        
    async def start_game_server(self, server_id: str):
        """"""
        url = f"/api/0.1/game-servers/{server_id}/start"

        try:
            async with self.session.post(url=url) as resp:
                await resp.json()
                return resp.ok
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError
        
    async def update_game_server_mode(self, server_id: str, game_mode):
        """"""
        url = f"/api/0.1/game-servers/{server_id}"
        payload = {
            "cs2_settings.game_mode": game_mode
        }

        try:
            async with self.session.put(url=url, data=payload) as resp:
                await resp.json()
                return resp.ok
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError

    async def send_rcon_to_game_server(self, server_id: str, cmd: str):
        """"""
        url = f"/api/0.1/game-servers/{server_id}/console"
        payload = {
            'line': cmd
        }

        try:
            async with self.session.post(url=url, data=payload) as resp:
                await resp.json()
                return resp.ok
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError

    async def get_match(self, match_id: str) -> Optional["Match"]:
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}"

        try:
            async with self.session.get(url=url) as resp:
                resp_data = await resp.json()
                if not resp.ok:
                    return
                return Match.from_dict(resp_data)
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError
        
    async def create_match(
        self,
        game_server_id: str,
        map_name: str,
        team1_name: str,
        team2_name: str,
        players: List[dict]
    ) -> Match:
        """"""

        url = "/api/0.1/cs2-matches"

        payload = {
            'game_server_id': game_server_id,
            'team1': { 'name': team1_name },
            'team2': { 'name': team2_name },
            'players': players,
            'settings': {
                'map': map_name,
                'connect_time': 300,
                'match_begin_countdown': 15
            }
        }

        try:
            async with self.session.post(url=url, json=payload) as resp:
                resp_data = await resp.json()
                if not resp.ok:
                    raise ValueError(resp_data)
                return Match.from_dict(resp_data)
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError

    async def add_match_player(
        self,
        match_id: int,
        steam_id: str,
        team: Literal["team1", "team2", "spectator"]
    ):
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}/players"
        payload = {
            'steam_id_64': steam_id,
            'team': team,
        }

        try:
            async with self.session.put(url=url, json=payload) as resp:
                await resp.json()
                return resp.ok
        except Exception as e:
            self.logger.error(e, exc_info=1)
            raise APIError
                

api = APIManager()
