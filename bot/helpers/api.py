# bot/helpers/api.py

import discord
import asyncio
import logging
import json
import aiohttp
from datetime import datetime
from typing import Literal, Union, Optional, List, Dict

from bot.helpers.db import db
from bot.helpers.configs import Config
from bot.helpers.errors import APIError, AuthError


def check_connection(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (AuthError, APIError) as e:
            raise APIError("API Error: " + e.message)
        except Exception as e:
            raise APIError("API connection error!")
    return wrapper


class Match:
    """"""

    def __init__(self, match_data: dict) -> None:
        """"""
        self.id = match_data['id']
        self.user_id = match_data['user_id']
        self.server_id = match_data['server_id']
        self.team1_id = match_data['team1_id']
        self.team2_id = match_data['team2_id']
        self.winner = match_data['winner']
        self.team1_score = match_data['team1_score']
        self.team2_score = match_data['team2_score']
        self.team1_string = match_data['team1_string']
        self.team2_string = match_data['team2_string']
        self.cancelled = match_data['cancelled']
        self.forfeit = match_data['forfeit']
        self.start_time = match_data['start_time']
        self.end_time = match_data['end_time']
        self.title = match_data['title']
        self.max_maps = match_data['max_maps']
        self.season_id = match_data['season_id']
        self.is_pug = match_data['is_pug']

    @classmethod
    def from_dict(cls, data: dict) -> "Match":
        return cls(data)


class MapStat:
    """"""

    def __init__(self, data: dict) -> None:
        """"""
        self.id = data['id']
        self.match_id = data['match_id']
        self.winner = data['winner']
        self.map_number = data['map_number']
        self.map_name = data['map_name']
        self.team1_score = data['team1_score']
        self.team2_score = data['team2_score']
        self.start_time = data['start_time']
        self.end_time = data['end_time']

    @classmethod
    def from_dict(cls, data: dict) -> "MapStat":
        return cls(data)


class PlayerStat:
    """"""

    def __init__(self, data: dict) -> None:
        """"""
        self.steam = data["steamId"]
        self.name = data["name"]
        self.kills = data["kills"]
        self.deaths = data["deaths"]
        self.assists = data["assists"]
        self.k1 = data["k1"]
        self.k2 = data["k2"]
        self.k3 = data["k3"]
        self.k4 = data["k4"]
        self.k5 = data["k5"]
        self.v1 = data["v1"]
        self.v2 = data["v2"]
        self.v3 = data["v3"]
        self.v4 = data["v4"]
        self.v5 = data["v5"]
        self.headshots = data["hsk"]
        self.hsp = f'{float(data["hsp"]):.0f}%'
        self.rating = float(data["average_rating"])
        self.wins = data["wins"]
        self.played = data["total_maps"]

    @property
    def win_percent(self):
        """"""
        return f'{self.wins / self.played * 100:.0f}%' if self.played else '0%'

    @property
    def kdr(self):
        """"""
        return f'{self.kills / self.deaths:.0f}%' if self.deaths else '0%'

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerStat":
        return cls(data)


class Server:
    """"""

    def __init__(self, server_data: dict) -> None:
        """"""
        self.id = server_data['id']
        self.ip_string = server_data['ip_string']
        self.port = server_data['port']
        self.gotv_port = server_data['gotv_port']
        self.display_name = server_data['display_name']
        self.flag = server_data['flag']
        self.public_server = server_data['public_server']
        self.in_use = server_data['in_use']

    @classmethod
    def from_dict(cls, data: dict) -> "Server":
        return cls(data)


class Team:
    """"""

    def __init__(self, team_data: dict) -> None:
        """"""
        self.id = team_data['id']
        self.user_id = team_data['user_id']
        self.name = team_data['name']
        self.tag = team_data['tag']
        self.flag = team_data['flag']
        self.logo = team_data['logo']
        self.public_team = team_data['public_team']
        self.auth_name = team_data['auth_name']

    @classmethod
    def from_dict(cls, data: dict) -> "Team":
        return cls(data)


async def start_request_log(session, ctx, params):
    """"""
    ctx.start = asyncio.get_event_loop().time()
    logger = logging.getLogger('API')
    logger.info(f'Sending {params.method} request to {params.url}')


async def end_request_log(session, ctx, params):
    """"""
    logger = logging.getLogger('API')
    elapsed = asyncio.get_event_loop().time() - ctx.start
    logger.info(f'Response received from {params.url} ({elapsed:.2f}s)\n'
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

        # Register trace config handlers
        trace_config = aiohttp.TraceConfig()
        trace_config.on_request_start.append(start_request_log)
        trace_config.on_request_end.append(end_request_log)

    def connect(self, loop):
        self.logger.info('Starting API helper client session')
        self.session = aiohttp.ClientSession(
            base_url=Config.base_url,
            loop=loop,
            headers={"user-api": Config.api_key},
            json_serialize=lambda x: json.dumps(x, ensure_ascii=False),
            timeout=aiohttp.ClientTimeout(total=30),
            trace_configs=[TRACE_CONFIG]
        )

    async def close(self):
        """ Close the API helper's session. """
        self.logger.info('Closing API helper client session')
        await self.session.close()

    @check_connection
    async def get_team(self, team_id: int):
        """"""
        url = f"/api/teams/{team_id}"

        async with self.session.get(url=url) as resp:
            resp_data = await resp.json()
            return Team.from_dict(resp_data['team'])

    @check_connection
    async def create_team(self, name: str, users_dict: Dict[str, Dict[str, bool]]):
        """"""
        url = "/api/teams"
        data = {
            'name': 'team_' + name,
            'public_team': 0,
            'auth_name': users_dict
        }

        async with self.session.post(url=url, json=[data]) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            resp_data = await resp.json()
            if resp.status >= 400:
                raise APIError(resp_data['message'])
            return resp_data['id']

    @check_connection
    async def delete_team(self, team_id: int):
        """"""
        url = "/api/teams"
        data = {'team_id': team_id}

        async with self.session.delete(url=url, json=[data]) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            return resp.status

    @check_connection
    async def add_team_member(self, team_id: int, user_dict: Dict[str, Dict[str, bool]]):
        """"""
        url = "/api/teams"
        data = {
            'id': team_id,
            'auth_name': user_dict
        }

        async with self.session.put(url=url, json=[data]) as resp:
            return resp.status < 400

    @check_connection
    async def remove_team_member(self, team_id: int, steam_id: str):
        """"""
        url = "/api/teams"
        data = {
            'team_id': team_id,
            'steam_id': steam_id
        }

        async with self.session.delete(url=url, json=[data]) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            return resp.status

    @check_connection
    async def get_server(self, server_id: int):
        """"""
        url = f"/api/servers/{server_id}"

        async with self.session.get(url=url) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            resp_data = await resp.json()
            return Server.from_dict(resp_data['server'])

    @check_connection
    async def get_servers(self):
        """"""
        url = "/api/servers/myservers"

        async with self.session.get(url=url) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            resp_data = await resp.json()
            return [Server.from_dict(server) for server in resp_data['servers']]

    @check_connection
    async def is_server_available(self, server_id: int):
        """ 
        """
        url = f"/api/servers/{server_id}/status"

        async with self.session.get(url=url) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            return resp.status < 400

    @check_connection
    async def get_playerstat(self, user: discord.Member, bot) -> Optional[PlayerStat]:
        """
        Retrieve players stats from the API PUG stats.

        Args:
        - user: discord.Member object.

        Returns:
        - PlayerState object if the player existed in the API database, Otherwise return None.
        """
        user_model = await db.get_user_by_discord_id(user.id, bot)
        if not user_model:
            return
        url = f"/api/playerstats/{user_model.steam}/pug"

        async with self.session.get(url=url) as resp:
            if resp.status < 400:
                resp_data = await resp.json()
                resp_data["playerstats"]["name"] = user.display_name
                return PlayerStat.from_dict(resp_data["playerstats"])

    @check_connection
    async def get_leaderboard(self, users: List[discord.Member]) -> List[PlayerStat]:
        """
        Retrieve players stats from the PUG leaderboard API and matches them to the given list of discord.Member.

        Args:
        - users: A list of discord.Member objects.

        Returns:
        - A list of PlayerStat objects.
        """

        url = "/api/leaderboard/players/pug"

        users_model = await db.get_users(users)
        db_steam_ids = [usr.steam for usr in users_model]

        async with self.session.get(url=url) as resp:
            resp_data = await resp.json()
            if resp.status >= 400:
                raise APIError(resp_data['message'])
            players = list(
                filter(lambda x: x['steamId'] in db_steam_ids, resp_data['leaderboard']))
            api_steam_ids = [player['steamId'] for player in players]

            for steam_id in db_steam_ids:
                if steam_id not in api_steam_ids:
                    players.append({
                        "steamId": steam_id,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "k1": 0,
                        "k2": 0,
                        "k3": 0,
                        "k4": 0,
                        "k5": 0,
                        "v1": 0,
                        "v2": 0,
                        "v3": 0,
                        "v4": 0,
                        "v5": 0,
                        "trp": 0,
                        "fba": 0,
                        "total_damage": 0,
                        "hsk": 0,
                        "hsp": 0.00,
                        "average_rating": 0.00,
                        "wins": 0,
                        "total_maps": 0
                    })

            players.sort(key=lambda x: db_steam_ids.index(x['steamId']))
            for idx, db_user in enumerate(users_model):
                players[idx]['name'] = db_user.user.display_name

            return [PlayerStat.from_dict(player) for player in players]

    @check_connection
    async def get_mapstats(self, match_id: int):
        """
        Fetches map statistics for a match from the API server.

        Args:
        - match_id: The ID of the match for which to fetch map statistics.

        Returns:
        - A list of `MapStat` objects representing the map statistics for the specified match.

        Raises:
        - `APIError`: If an error occurs while fetching the map statistics.
        """

        url = f"/api/mapstats/{match_id}"

        async with self.session.get(url=url) as resp:
            resp_data = await resp.json()
            return [MapStat.from_dict(map_stat) for map_stat in resp_data['mapstats']]

    @check_connection
    async def get_match(self, match_id: int) -> Union["Match", None]:
        """
        Fetches a match from the API server.

        Args:
        - match_id: The ID of the match to fetch.

        Returns:
        - If successful, a `Match` object representing the fetched match. If the match not found, 
          `None` is returned.

        Raises:
        - `APIError`: If an error occurs while fetching the match.
        """

        url = f"/api/matches/{match_id}"

        async with self.session.get(url=url) as resp:
            if resp.status < 400:
                resp_data = await resp.json()
                return Match.from_dict(resp_data["match"])

    @check_connection
    async def create_match(
        self,
        server_id: int,
        team1_id: int,
        team2_id: int,
        str_maps: str,
        total_players: int,
        game_mode: Literal["competitive", "wingman"],
        pug: bool=True
    ) -> int:
        """
        Sends an HTTP POST request to create a new match.

        Args:
            server_id (int): The ID of the server on which to create the match.
            team1_id (int): The ID of the first team in the match.
            team2_id (int): The ID of the second team in the match.
            str_maps (str): A string containing the maps to be played in the match.
            total_players (int): The total number of players in the match.
            game_mode (Literal["competitive", "wingman"]): The game mode to be played in the match.

        Returns:
            int: The ID of the newly created match.

        Raises:
            APIError: If there was an error with the API request or response.
        """

        url = "/api/matches"

        data = {
            'server_id': server_id,
            'team1_id': team1_id,
            'team2_id': team2_id,
            'title': '[PUG] Map {MAPNUMBER} of {MAXMAPS}',
            'wingman': game_mode == 'wingman',
            'is_pug': pug,
            'start_time': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            'ignore_server': 0,
            'max_maps': len(str_maps.split()),
            'veto_mappool': str_maps,
            'skip_veto': 1,
            'veto_first': 'team1',
            'side_type': 'always_knife',
            'players_per_team': total_players // 2,
            'min_players_to_ready': total_players // 2,
            'match_cvars': {
                'sv_hibernate_when_empty': 0,
                'get5_time_to_start': 300,
            }
        }

        async with self.session.post(url=url, json=[data]) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            resp_data = await resp.json()
            return resp_data['id']

    @check_connection
    async def cancel_match(self, match_id: int):
        """
        Sends an HTTP GET request to cancel the match with the given ID.

        Args:
            match_id (int): The ID of the match to cancel.

        Returns:
            bool: True if the match was successfully cancelled.

        Raises:
            APIError: If there was an error with the API request or response.
        """

        url = f"/api/matches/{match_id}/cancel"

        async with self.session.get(url=url) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            if resp.status >= 400:
                resp_data = await resp.json()
                raise APIError(resp_data['message'])
            return True

    @check_connection
    async def restart_match(self, match_id: int):
        """
        Sends an HTTP GET request to restart the match with the given ID.

        Args:
            match_id (int): The ID of the match to restart.

        Returns:
            bool: True if the match was successfully restarted.

        Raises:
            APIError: If there was an error with the API request or response.
        """

        url = f"/api/matches/{match_id}/restart"

        async with self.session.get(url=url) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            if resp.status >= 400:
                resp_data = await resp.json()
                raise APIError(resp_data['message'])
            return True

    @check_connection
    async def pause_match(self, match_id: int):
        """
        Sends an HTTP GET request to pause a match with the given ID.

        Args:
            match_id (int): The ID of the match to pause.

        Returns:
            bool: True if the match was successfully paused.

        Raises:
            APIError: If there was an error with the API requset or response.
        """

        url = f"/api/matches/{match_id}/pause"

        async with self.session.get(url=url) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            if resp.status >= 400:
                resp_data = await resp.json()
                raise APIError(resp_data['message'])
            return True

    @check_connection
    async def unpause_match(self, match_id: int) -> bool:
        """
        Sends an HTTP GET request to unpause a match with the given ID.

        Args:
            match_id (int): The ID of the match to unpause.

        Returns:
            bool: True if the match was successfully unpaused.

        Raises:
            APIError: If there was an error with the API requset or response.
        """

        url = f"/api/matches/{match_id}/unpause"

        async with self.session.get(url=url) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            if resp.status >= 400:
                resp_data = await resp.json()
                raise APIError(resp_data['message'])
            return True

    @check_connection
    async def add_match_player(
        self,
        match_id: int,
        steam_id: str,
        nickname: str,
        team_str: Literal["team1", "team2", "spec"]
    ):
        """
        Sends an HTTP PUT request to add a player with the given Steam ID and nickname to the specified team 
        in the given match ID.

        Args:
            match_id (int): The ID of the match to add the player into.
            steam_id (str): The Steam ID of the player to add.
            nickname (str): The nickname of the player to add.
            team_str (Literal["team1", "team2", "spec"]): The team to add the player into. Must be either "team1", "team2", 
                or "spec" to add the player as a spectator.

        Returns:
            bool: True if the player was successfully added into the match.

        Raises:
            APIError: If there was an error with the API request or response.
        """

        url = f"/api/matches/{match_id}/{'addspec' if team_str == 'spec' else 'adduser'}"
        data = {
            'steam_id': steam_id,
            'team_id': team_str,
            'nickname': nickname
        }

        async with self.session.put(url=url, json=[data]) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            if resp.status >= 400:
                resp_data = await resp.json()
                raise APIError(resp_data['message'])
            return True

    @check_connection
    async def remove_match_player(self, match_id: int, steam_id: str):
        """
        Sends an HTTP PUT request to remove a player with the given Steam ID from the given match ID.

        Args:
            match_id (int): The ID of the match to remove the player from.
            steam_id (str): The Steam ID of the player to remove.

        Returns:
            bool: True if the player was successfully removed from the match.

        Raises:
            APIError: If there was an error with the API request or response.
        """

        url = f"/api/matches/{match_id}/removeuser"
        data = {'steam_id': steam_id}

        async with self.session.put(url=url, json=[data]) as resp:
            if "/auth/steam" in str(resp.url):
                raise AuthError
            if resp.status >= 400:
                resp_data = await resp.json()
                raise APIError(resp_data['message'])
            return True


api = APIManager()
