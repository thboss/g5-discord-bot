
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import Sessions, Config
from ..utils import Utils


class Teams:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.user_id = data['user_id']
        self.name = data['name']
        self.tag = data['tag']
        self.flag = data['flag']
        self.logo = data['logo']
        self.public_team = data['public_team']
        self.auth_name = data['auth_name']

    @classmethod
    async def get_team(cls, team_id: int):
        """"""
        url = f"{Config.api_url}/teams/{team_id}"

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return cls(resp_data['team'])
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @staticmethod
    async def create_team(headers, name, db_users):
        """"""
        url = f"{Config.api_url}/teams"
        data = {
            'name': name,
            'flag': db_users[0].flag,
            'public_team': 0,
            'auth_name': {
                db_user.steam: {
                    'name': db_user.user.display_name,
                    'captain': index == 0
                } for index, db_user in enumerate(db_users)
            }
        }

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

    @staticmethod
    async def delete_team(headers, team_id):
        """"""
        url = f"{Config.api_url}/teams"
        data = {'team_id': team_id}

        try:
            async with Sessions.requests.delete(url=url, json=[data], headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @staticmethod
    async def add_team_member(headers, team_id, steam_id, nickname, captain=False):
        """"""
        url = f"{Config.api_url}/teams"
        data = {
            'id': team_id,
            'auth_name': {
                steam_id: {
                    'name': nickname,
                    'captain': captain
                }
            }
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

    @staticmethod
    async def remove_team_member(headers, team_id, steam_id):
        """"""
        url = f"{Config.api_url}/teams"
        data = {
            'team_id': team_id,
            'steam_id': steam_id
        }

        try:
            async with Sessions.requests.delete(url=url, json=[data], headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))
