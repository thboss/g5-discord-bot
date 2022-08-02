
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import Sessions, Config
from ..utils import Utils


class MapStats:
    """"""

    def __init__(self, data) -> None:
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
    async def get_mapstats(cls, match_id: int):
        """"""
        url = f"{Config.api_url}/mapstats/{match_id}"

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return [cls(map_stat) for map_stat in resp_data['mapstats']]
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))
