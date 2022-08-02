# resources.py

from aiohttp import ClientSession


class Sessions:
    requests: ClientSession


class Config:
    api_url: str
    g5v_url: str
    discord_token: str
    prefixes: list
    lang: str


class G5:
    bot: None
    db: None
