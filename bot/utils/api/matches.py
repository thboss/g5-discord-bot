
from datetime import datetime
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import Sessions, Config
from ..utils import Utils


class Scoreboard:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.match_id = data['match_id']
        self.map_id = data['map_id']
        self.team_id = data['team_id']
        self.steam_id = data['steam_id']
        self.name = data['name']
        self.kills = data['kills']
        self.headshot_kills = data['headshot_kills']
        self.deaths = data['deaths']
        self.assists = data['assists']
        self.flashbang_assists = data['flashbang_assists']
        self.roundsplayed = data['roundsplayed']
        self.teamkills = data['teamkills']
        self.suicides = data['suicides']
        self.damage = data['damage']
        self.bomb_plants = data['bomb_plants']
        self.bomb_defuses = data['bomb_defuses']
        self.v1 = data['v1']
        self.v2 = data['v2']
        self.v3 = data['v3']
        self.v4 = data['v4']
        self.v5 = data['v5']
        self.k1 = data['k1']
        self.k2 = data['k2']
        self.k3 = data['k3']
        self.k4 = data['k4']
        self.k5 = data['k5']
        self.firstdeath_ct = data['firstdeath_ct']
        self.firstdeath_t = data['firstdeath_t']
        self.firstkill_ct = data['firstkill_ct']
        self.firstkill_t = data['firstkill_t']
        self.kast = data['kast']
        self.contribution_score = data['contribution_score']
        self.winner = data['winner']
        self.mvp = data['mvp']
        self.team_name = data['team_name']


class Matches:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.user_id = data['user_id']
        self.server_id = data['server_id']
        self.team1_id = data['team1_id']
        self.team2_id = data['team2_id']
        self.winner = data['winner']
        self.team1_score = data['team1_score']
        self.team2_score = data['team2_score']
        self.team1_string = data['team1_string']
        self.team2_string = data['team2_string']
        self.cancelled = data['cancelled']
        self.forfeit = data['forfeit']
        self.start_time = data['start_time']
        self.end_time = data['end_time']
        self.title = data['title']
        self.max_maps = data['max_maps']
        self.season_id = data['season_id']
        self.is_pug = data['is_pug']

    @classmethod
    async def get_stats(cls, match_id):
        """"""
        url = f"{Config.api_url}/matches/{match_id}"

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return cls(resp_data['match'])
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    async def get_scoreboard(match_id: int):
        """"""
        url = f"{Config.api_url}/playerstats/match/{match_id}"

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return [Scoreboard(player_stat) for player_stat in resp_data['playerstats']]
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @staticmethod
    async def create(
        headers,
        server_id,
        team1_id,
        team2_id,
        season_id,
        str_maps,
        total_players,
        pug,
        start_time=None,
        cvars=None,
    ):
        """"""
        url = f"{Config.api_url}/matches"

        data = {
            'server_id': server_id,
            'team1_id': team1_id,
            'team2_id': team2_id,
            'season_id': season_id,
            'title': '[PUG] Map {MAPNUMBER} of {MAXMAPS}',
            'is_pug': pug,
            'start_time': start_time or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
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
                'get5_end_match_on_empty_server': 1
            }
        }

        if cvars:
            for k, v in cvars.items():
                data['match_cvars'][k] = v

        try:
            async with Sessions.requests.post(url=url, json=[data], headers=headers) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return resp_data['id']
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    async def cancel(self, headers, winner=None):
        """"""
        if winner:
            url = f"{Config.api_url}/matches/{self.id}/forfeit/{winner}"
        else:
            url = f"{Config.api_url}/matches/{self.id}/cancel"

        try:
            async with Sessions.requests.get(url=url, headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    async def add_player(self, headers, steam_id, nickname, team_str):
        """"""
        url = f"{Config.api_url}/matches/{self.id}/{'addspec' if team_str == 'spec' else 'adduser'}"
        data = {
            'steam_id': steam_id,
            'team_id': team_str,
            'nickname': nickname
        }

        try:
            async with Sessions.requests.put(url=url, json=[data], headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    async def remove_player(self, headers, steam_id):
        """"""
        url = f"{Config.api_url}/matches/{self.id}/removeuser"
        data = {'steam_id': steam_id}

        try:
            async with Sessions.requests.put(url=url, json=[data], headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    async def pause(self, headers):
        """"""
        url = f"{Config.api_url}/matches/{self.id}/pause"

        try:
            async with Sessions.requests.get(url=url, headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    async def unpause(self, headers):
        """"""
        url = f"{Config.api_url}/matches/{self.id}/unpause"

        try:
            async with Sessions.requests.get(url=url, headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))
