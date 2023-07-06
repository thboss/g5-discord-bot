from steam.steamid import SteamID, from_url
import math

from .errors import CustomError


def validate_steam(steam: str) -> int:
    try:
        steam_id = SteamID(steam)
    except:
        raise CustomError("Invalid Steam!")

    if not steam_id.is_valid():
        steam_id = from_url(steam, http_timeout=15)
        if steam_id is None:
            steam_id = from_url(
                f'https://steamcommunity.com/id/{steam}/', http_timeout=15)
            if steam_id is None:
                raise CustomError("Invalid Steam!")

    return steam_id


def indent(string, n=4):
    """"""
    indent = ' ' * n
    return indent + string.replace('\n', '\n' + indent)


def align_text(text, length, align='center'):
    """ Center the text within whitespace of input length. """
    if length < len(text):
        return text

    whitespace = length - len(text)

    if align == 'center':
        pre = math.floor(whitespace / 2)
        post = math.ceil(whitespace / 2)
    elif align == 'left':
        pre = 0
        post = whitespace
    elif align == 'right':
        pre = whitespace
        post = 0
    else:
        raise ValueError('Align argument must be "center", "left" or "right"')

    return ' ' * pre + text + ' ' * post
