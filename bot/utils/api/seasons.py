
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import Sessions, Config
from ..utils import Utils


class Seasons:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.name = data['name']
        self.start_date = data['start_date']
        self.end_date = data['end_date']

    @classmethod
    async def get_season(cls, season_id):
        """"""
        url = f"{Config.api_url}/seasons/{season_id}"

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return cls(resp_data['season'])
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @classmethod
    async def my_seasons(cls, headers, only_active=False):
        """"""
        url = f"{Config.api_url}/seasons/myseasons/"
        if only_active:
            url += 'available'

        try:
            async with Sessions.requests.get(url=url, headers=headers) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return [cls(season) for season in resp_data['seasons']]
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))
