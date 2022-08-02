
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import Sessions, Config
from ..utils import Utils


class Servers:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.ip_string = data['ip_string']
        self.port = data['port']
        self.gotv_port = data['gotv_port']
        self.display_name = data['display_name']
        self.flag = data['flag']
        self.public_server = data['public_server']
        self.in_use = data['in_use']

    @property
    def connect_info(self):
        """"""
        connect_url = f'steam://connect/{self.ip_string}:{self.port}'
        connect_command = f'connect {self.ip_string}:{self.port}'
        connect_gotv = f'GOTV: steam://connect/{self.ip_string}:{self.gotv_port}\n\n'
        return f'{Utils.trans("match-server-info", connect_url, connect_command)}\n\n' + connect_gotv

    @classmethod
    async def get_server(cls, headers, server_id: int):
        """"""
        url = f"{Config.api_url}/servers/{server_id}"

        try:
            async with Sessions.requests.get(url=url, headers=headers) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return cls(resp_data['server'])
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @classmethod
    async def get_servers(cls, headers):
        """"""
        url = f"{Config.api_url}/servers/myservers"

        try:
            async with Sessions.requests.get(url=url, headers=headers) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                return [cls(server) for server in resp_data['servers']]
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @staticmethod
    async def is_server_available(headers, server_id):
        """"""
        url = f"{Config.api_url}/servers/{server_id}/status"

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
