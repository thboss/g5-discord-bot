
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import G5, Sessions, Config
from ..utils import Utils


async def check_auth(headers):
    """"""
    try: # in some cases api must end with slash to work 
        async with Sessions.requests.get(url=Config.api_url + '/', headers=headers) as resp:
            resp_data = await resp.json()
            G5.bot.logger.info('Response: ' + resp_data['message'])
    except ContentTypeError:
        raise Exception(Utils.trans('invalid-api-key'))
    except (ClientConnectionError, TimeoutError):
        raise Exception(Utils.trans('connect-api-error'))
