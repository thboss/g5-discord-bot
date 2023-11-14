# bot/helpers/api.py

import asyncio
import logging
import json
import aiohttp
from typing import Literal, Optional, List
from bot.helpers.configs import Config
from bot.helpers.errors import APIError


class MatchPlayer:
    def __init__(self, data, winner):
        self.match_id = data['match_id']
        self.steam_id = data['steam_id_64']
        self.team = data['team']
        self.connected = data['connected']
        self.kicked = data['kicked']
        self.kills = data['stats']['kills']
        self.assists = data['stats']['assists']
        self.headshots = data['stats']['kills_with_headshot']
        self.deaths = data['stats']['deaths']
        self.mvps = data['stats']['mvps']
        self.k2 = data['stats']['2ks']
        self.k3 = data['stats']['3ks']
        self.k4 = data['stats']['4ks']
        self.k5 = data['stats']['5ks']
        self.score = data['stats']['score']
        self.winner = winner
        self.member = None

    @classmethod
    def from_dict(cls, data: dict, winner) -> "MatchPlayer":
        return cls(data, winner)


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
        self.team1_players = [MatchPlayer.from_dict(player, self.team1_score > self.team2_score) for player in match_data['players'] if player['team'] == 'team1']
        self.team2_players = [MatchPlayer.from_dict(player, self.team1_score < self.team2_score) for player in match_data['players'] if player['team'] == 'team2']

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
            loop=loop,
            json_serialize=lambda x: json.dumps(x, ensure_ascii=False),
            timeout=aiohttp.ClientTimeout(total=30),
            trace_configs=[TRACE_CONFIG] if Config.debug else None
        )

    async def close(self):
        """ Close the API helper's session. """
        self.logger.info('Closing API helper client session')
        await self.session.close()

    async def check_auth(self, email, password):
        """"""
        url = "/api/0.1/account"
        auth = aiohttp.BasicAuth(email, password)

        async with self.session.get(url=url, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            return resp.ok

    async def get_game_server(self, game_server_id: str, auth: aiohttp.BasicAuth=None) -> "GameServer":
        """"""
        url = f"/api/0.1/game-servers/{game_server_id}"

        async with self.session.get(url=url, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            resp_data = await resp.json()
            return GameServer.from_dict(resp_data)
        
    async def get_game_servers(self, auth: aiohttp.BasicAuth=None) -> List[GameServer]:
        """"""
        url = f"/api/0.1/game-servers"

        async with self.session.get(url=url, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            resp_data = await resp.json()
            return [GameServer.from_dict(game_server) for game_server in resp_data if game_server['game'] == 'cs2']
        
    async def update_game_server(
        self, server_id: str,
        game_mode: Literal["competitive", "wingman"]=None,
        location: str=None,
        auth: aiohttp.BasicAuth=None
    ):
        """"""
        url = f"/api/0.1/game-servers/{server_id}"
        payload = {}
        if game_mode: payload["cs2_settings.game_mode"] = game_mode
        if location: payload["location"] = location

        async with self.session.put(url=url, data=payload, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            return resp.ok
        
    async def stop_game_server(self, server_id: str, auth: aiohttp.BasicAuth=None):
        """"""
        url = f"/api/0.1/game-servers/{server_id}/stop"

        async with self.session.post(url=url, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            return resp.ok

    async def get_match(self, match_id: str, auth: aiohttp.BasicAuth=None) -> Optional["Match"]:
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}"

        async with self.session.get(url=url, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            resp_data = await resp.json()
            return Match.from_dict(resp_data)
        
    async def create_match(
        self,
        game_server_id: str,
        map_name: str,
        team1_name: str,
        team2_name: str,
        match_players: List[dict],
        connect_time,
        api_key: str,
        auth: aiohttp.BasicAuth=None
    ) -> Match:
        """"""

        url = "/api/0.1/cs2-matches"

        payload = {
            'game_server_id': game_server_id,
            'team1': { 'name': 'team_' + team1_name },
            'team2': { 'name': 'team_' + team2_name },
            'players': match_players,
            'settings': {
                'map': map_name,
                'connect_time': connect_time,
                'match_begin_countdown': 15
            },
            'webhooks': {
                'match_end_url': f'http://{Config.webserver_host}:{Config.webserver_port}/cs2bot-api/match-end',
                'round_end_url': f'http://{Config.webserver_host}:{Config.webserver_port}/cs2bot-api/round-end',
                'authorization_header': api_key
            }
        }

        async with self.session.post(url=url, json=payload, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            resp_data = await resp.json()
            return Match.from_dict(resp_data)

    async def add_match_player(
        self,
        match_id: int,
        steam_id: str,
        team: Literal["team1", "team2", "spectator"],
        auth: aiohttp.BasicAuth=None
    ):
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}/players"
        payload = {
            'steam_id_64': steam_id,
            'team': team,
        }

        async with self.session.put(url=url, json=payload, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            return resp.ok
                
    async def cancel_match(self, match_id: int, auth: aiohttp.BasicAuth=None):
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}/cancel"

        async with self.session.post(url=url, auth=auth) as resp:
            if resp.status == 401:
                raise APIError("Invalid credentials! Please use command `/auth` to update your credentials.")
            return resp.ok
        

api = APIManager()
