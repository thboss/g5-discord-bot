
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import Sessions, Config
from ..utils import Utils


class PlayerStats:
    """"""

    def __init__(self, data) -> None:
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
        self.hsp = data["hsp"]
        self.rating = data["average_rating"]
        self.wins = data["wins"]
        self.played = data["total_maps"]

    @property
    def win_percent(self):
        """"""
        return f'{self.wins / self.played * 100:.2f}' if self.played else '0.00'

    @property
    def kdr(self):
        """"""
        return f'{self.kills / self.deaths:.2f}' if self.deaths else '0.00'

    @classmethod
    async def get_player_stats(cls, db_user, pug=False, season_id=None):
        """"""
        url = f"{Config.api_url}/playerstats/{db_user.steam}/{'pug' if pug else 'official'}/"
        if season_id:
            url += f"season/{season_id}"

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                resp_data["name"] = db_user.user.display_name
                return cls(resp_data)
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @classmethod
    async def get_leaderboard(cls, users, pug=False, season_id=None):
        """"""
        url = f"{Config.api_url}/leaderboard/players/"
        if pug:
            url += "pug/"
        elif season_id:
            url += f"season/{season_id}"

        db_steam_ids = [usr.steam for usr in users]

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                players = list(
                    filter(lambda x: x['steam'] in db_steam_ids, resp_data['leaderboard']))
                api_steam_ids = [player['steam'] for player in players]

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
                            "hsp": "0.00",
                            "average_rating": "0.00",
                            "wins": 0,
                            "total_maps": 0
                        })

                players.sort(key=lambda x: db_steam_ids.index(x['steamId']))
                for idx, db_user in enumerate(users):
                    players[idx]['name'] = db_user.user.display_name

                return [cls(player) for player in players]
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))
