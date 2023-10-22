from steam.steamid import SteamID, from_url
from PIL import Image, ImageFont, ImageDraw
from discord import File
import math
import os

from .errors import CustomError


ABS_ROOT_DIR = os.path.abspath(os.curdir)
TEMPLATES_DIR = os.path.join(ABS_ROOT_DIR, 'assets', 'img', 'templates')
FONTS_DIR = os.path.join(ABS_ROOT_DIR, 'assets', 'fonts')
SAVE_IMG_DIR = os.path.join(ABS_ROOT_DIR, 'assets', 'img')


COUNTRY_FLAGS = [
    'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AO', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AW', 'AX',
    'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BL', 'BM', 'BN', 'BO', 'BQ',
    'BR', 'BS', 'BT', 'BV', 'BW', 'BY', 'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK',
    'CL', 'CM', 'CN', 'CO', 'CR', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM',
    'DO', 'DZ', 'EC', 'EE', 'EG', 'EH', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 'FO', 'FR',
    'GA', 'GB', 'GD', 'GE', 'GF', 'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GP', 'GQ', 'GR', 'GS',
    'GT', 'GU', 'GW', 'GY', 'HK', 'HM', 'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IM', 'IN',
    'IO', 'IQ', 'IR', 'IS', 'IT', 'JE', 'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN',
    'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK', 'LR', 'LS', 'LT', 'LU', 'LV',
    'LY', 'MA', 'MC', 'MD', 'ME', 'MF', 'MG', 'MH', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP', 'MQ',
    'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA', 'NC', 'NE', 'NF', 'NG', 'NI',
    'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG', 'PH', 'PK', 'PL', 'PM',
    'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 'RE', 'RO', 'RS', 'RU', 'RW', 'SA', 'SB', 'SC',
    'SD', 'SE', 'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST', 'SV',
    'SX', 'SY', 'SZ', 'TC', 'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO', 'TR',
    'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA', 'VC', 'VE', 'VG', 'VI',
    'VN', 'VU', 'WF', 'WS', 'YE', 'YT', 'ZA', 'ZM', 'ZW'
]


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


def calculate_elo(stats, old_elo=1000):
    weight = max(2 - 0.1 * ((old_elo - 800) / 100), 0.1)
    winner = 1 if stats.winner else -1
    new_elo = old_elo + round((
        stats.kills +
        stats.assists * 0.5 +
        stats.k2 * 2 +
        stats.k3 * 3 +
        stats.k4 * 4 +
        stats.k5 * 5 +
        winner * 5) * weight - \
        stats.deaths)
    
    return new_elo


def generate_statistics_img(stats):
    """"""
    width, height = 543, 745
    with Image.open(TEMPLATES_DIR + "/statistics.png") as img:
        font = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 25)
        draw = ImageDraw.Draw(img)
        fontbig = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 36)

        name = stats.member.display_name[:14]
        name_box = draw.textbbox((0, 0), name, font=fontbig)
        name_width = name_box[2] - name_box[0]

        draw.text(((width - name_width) // 2, 90), name, font=fontbig)
        draw.text((51, 226+109*0), align_text(str(stats.kills), 14), font=font)
        draw.text((51, 226+109*1), align_text(str(stats.deaths), 14), font=font)
        draw.text((51, 226+109*2), align_text(str(stats.assists), 14), font=font)
        draw.text((51, 226+109*3), align_text(str(stats.kdr), 14), font=font)
        draw.text((51, 226+109*4), align_text(str(stats.headshots), 14), font=font)
        draw.text((359, 226+109*0), align_text(str(stats.hsp), 20), font=font)
        draw.text((359, 226+109*1), align_text(str(stats.played_matches), 20), font=font)
        draw.text((359, 226+109*2), align_text(str(stats.wins), 20), font=font)
        draw.text((359, 226+109*3), align_text(str(stats.win_percent), 20), font=font)
        draw.text((359, 226+109*4), align_text(str(stats.elo), 20), font=font)

        img.save(SAVE_IMG_DIR + '/statistics.png')

    return File(SAVE_IMG_DIR + '/statistics.png')


def generate_leaderboard_img(players_stats):
    """"""
    width, height = 1096, 895

    with Image.open(TEMPLATES_DIR + "/leaderboard.png") as img:
        font = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 25)
        fontbig = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 36)
        draw = ImageDraw.Draw(img)

        title = 'Leaderboard'
        title_box = draw.textbbox((0, 0), title, font=fontbig)
        title_width = title_box[2] - title_box[0]

        draw.text(((width - title_width) // 2, 60), title, font=fontbig)

        for idx, p in enumerate(players_stats):
            draw.text((73, 235+65*idx), str(p.member.display_name)[:14], font=font)
            draw.text((340, 235+65*idx), str(p.kills), font=font)
            draw.text((500, 235+65*idx), str(p.deaths), font=font)
            draw.text((660, 235+65*idx), str(p.played_matches), font=font)
            draw.text((820, 235+65*idx), str(p.wins), font=font)
            draw.text((980, 235+65*idx), str(p.elo), font=font)

        img.save(SAVE_IMG_DIR + '/leaderboard.png')

    return File(SAVE_IMG_DIR + '/leaderboard.png')