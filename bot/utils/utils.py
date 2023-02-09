# utils.py

import json
import os
import asyncio

from discord import File
from dotenv import load_dotenv
from PIL import Image, ImageFont, ImageDraw
from functools import partial

from ..resources import Config


ABS_ROOT_DIR = os.path.abspath(os.curdir)
TEMPLATES_DIR = os.path.join(ABS_ROOT_DIR, 'assets', 'img', 'templates')
FONTS_DIR = os.path.join(ABS_ROOT_DIR, 'assets', 'fonts')
SAVE_IMG_DIR = os.path.join(ABS_ROOT_DIR, 'assets', 'img')

load_dotenv()

with open('translations.json', encoding="utf8") as f:
    translations = json.load(f)


def align_text(text, length, align='center'):
    """ Center the text within whitespace of input length. """
    if length < len(text):
        return text

    whitespace = length - len(text)

    if align == 'center':
        pre = round(whitespace / 2)
        post = round(whitespace / 2)
    elif align == 'left':
        pre = 0
        post = whitespace
    elif align == 'right':
        pre = whitespace
        post = 0
    else:
        raise ValueError('Align argument must be "center", "left" or "right"')

    return ' ' * pre + text + ' ' * post


async def delete_msgs(messages):
    """"""
    for msg in messages:
        try:
            await msg.delete()
        except:
            pass


class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()


class Utils:
    """"""

    FLAG_CODES = {
        '🇦🇨': 'AC', '🇦🇩': 'AD', '🇦🇪': 'AE', '🇦🇫': 'AF', '🇦🇬': 'AG', '🇦🇮': 'AI', '🇦🇱': 'AL',
        '🇦🇲': 'AM', '🇦🇴': 'AO', '🇦🇶': 'AQ', '🇦🇷': 'AR', '🇦🇸': 'AS', '🇦🇹': 'AT', '🇦🇺': 'AU',
        '🇦🇼': 'AW', '🇦🇽': 'AX', '🇦🇿': 'AZ', '🇧🇦': 'BA', '🇧🇧': 'BB', '🇧🇩': 'BD', '🇧🇪': 'BE', 
        '🇧🇫': 'BF', '🇧🇬': 'BG', '🇧🇭': 'BH', '🇧🇮': 'BI', '🇧🇯': 'BJ', '🇧🇱': 'BL', '🇧🇲': 'BM',
        '🇧🇳': 'BN', '🇧🇴': 'BO', '🇧🇶': 'BQ', '🇧🇷': 'BR', '🇧🇸': 'BS', '🇧🇹': 'BT', '🇧🇻': 'BV', 
        '🇧🇼': 'NW', '🇧🇾': 'BY', '🇧🇿': 'BZ', '🇨🇦': 'CA', '🇨🇨': 'CC', '🇨🇩': 'CD', '🇨🇫': 'CF', 
        '🇨🇬': 'CG', '🇨🇭': 'CH', '🇨🇮': 'CI', '🇨🇰': 'CK', '🇨🇱': 'CL', '🇨🇲': 'CM', '🇨🇳': 'CN', 
        '🇨🇴': 'CO', '🇨🇵': 'CP', '🇨🇷': 'CR', '🇨🇺': 'CU', '🇨🇻': 'CV', '🇨🇼': 'CW', '🇨🇽': 'CX', 
        '🇨🇾': 'CY', '🇨🇿': 'CZ', '🇩🇪': 'DE', '🇩🇬': 'DG', '🇩🇯': 'DJ', '🇩🇰': 'DK', '🇩🇲': 'DM', 
        '🇩🇴': 'DO', '🇩🇿': 'DZ', '🇪🇦': 'EA', '🇪🇨': 'EC', '🇪🇪': 'EE', '🇪🇬': 'EG', '🇪🇭': 'EH', 
        '🇪🇷': 'ER', '🇪🇸': 'ES', '🇪🇹': 'ET', '🇪🇺': 'EU', '🇫🇮': 'FI', '🇫🇯': 'FJ', '🇫🇰': 'FK', 
        '🇫🇲': 'FM', '🇫🇴': 'FO', '🇫🇷': 'FR', '🇬🇦': 'GA', '🇬🇧': 'GB', '🇬🇩': 'GD', '🇬🇪': 'GE', 
        '🇬🇫': 'GF', '🇬🇬': 'GG', '🇬🇭': 'GH', '🇬🇮': 'GI', '🇬🇱': 'GL', '🇬🇲': 'GM', '🇬🇳': 'GN', 
        '🇬🇵': 'GP', '🇬🇶': 'GQ', '🇬🇷': 'GR', '🇬🇸': 'GS', '🇬🇹': 'GT', '🇬🇺': 'GU', '🇬🇼': 'GW', 
        '🇬🇾': 'GY', '🇭🇰': 'HK', '🇭🇲': 'HM', '🇭🇳': 'HN', '🇭🇷': 'HR', '🇭🇹': 'HT', '🇭🇺': 'HU', 
        '🇮🇨': 'IC', '🇮🇩': 'ID', '🇮🇪': 'IE', '🇮🇱': 'IL', '🇮🇲': 'IM', '🇮🇳': 'IN', '🇮🇴': 'IO', 
        '🇮🇶': 'IQ', '🇮🇷': 'IR', '🇮🇸': 'IS', '🇮🇹': 'IT', '🇯🇪': 'JE', '🇯🇲': 'JM', '🇯🇴': 'JO', 
        '🇯🇵': 'JP', '🇰🇪': 'KE', '🇰🇬': 'KG', '🇰🇭': 'KH', '🇰🇮': 'KI', '🇰🇲': 'KM', '🇰🇳': 'KN', 
        '🇰🇵': 'KP', '🇰🇷': 'KR', '🇰🇼': 'KW', '🇰🇾': 'KY', '🇰🇿': 'KZ', '🇱🇦': 'LA', '🇱🇧': 'LB', 
        '🇱🇨': 'LC', '🇱🇮': 'LI', '🇱🇰': 'LK', '🇱🇷': 'LR', '🇱🇸': 'LS', '🇱🇹': 'LT', '🇱🇺': 'LU', 
        '🇱🇻': 'LV', '🇱🇾': 'LY', '🇲🇦': 'MS', '🇲🇨': 'MC', '🇲🇩': 'MD', '🇲🇪': 'ME', '🇲🇫': 'MF', 
        '🇲🇬': 'MG', '🇲🇭': 'MH', '🇲🇰': 'MK', '🇲🇱': 'ML', '🇲🇲': 'MM', '🇲🇳': 'MN', '🇲🇴': 'MO', 
        '🇲🇵': 'MP', '🇲🇶': 'MQ', '🇲🇷': 'MR', '🇲🇸': 'MS', '🇲🇹': 'MT', '🇲🇺': 'MU', '🇲🇻': 'MV', 
        '🇲🇼': 'MW', '🇲🇽': 'MX', '🇲🇾': 'MY', '🇲🇿': 'MZ', '🇳🇦': 'NA', '🇳🇨': 'NC', '🇳🇪': 'NE', 
        '🇳🇫': 'NF', '🇳🇬': 'NG', '🇳🇮': 'NI', '🇳🇱': 'NL', '🇳🇴': 'NO', '🇳🇵': 'NP', '🇳🇷': 'NR', 
        '🇳🇺': 'NU', '🇳🇿': 'NZ', '🇴🇲': 'OM', '🇵🇦': 'PA', '🇵🇪': 'PE', '🇵🇫': 'PF', '🇵🇬': 'PG', 
        '🇵🇭': 'PH', '🇵🇰': 'PK', '🇵🇱': 'PL', '🇵🇲': 'PM', '🇵🇳': 'PN', '🇵🇷': 'PR', '🇵🇸': 'PS', 
        '🇵🇹': 'PT', '🇵🇼': 'PW', '🇵🇾': 'PY', '🇶🇦': 'QA', '🇷🇪': 'RE', '🇷🇴': 'RO', '🇷🇸': 'RS', 
        '🇷🇺': 'RU', '🇷🇼': 'RW', '🇸🇦': 'SA', '🇸🇧': 'SB', '🇸🇨': 'SC', '🇸🇩': 'SD', '🇸🇪': 'SE', 
        '🇸🇬': 'SG', '🇸🇭': 'SH', '🇸🇮': 'SI', '🇸🇯': 'SJ', '🇸🇰': 'SK', '🇸🇱': 'SL', '🇸🇲': 'SM', 
        '🇸🇳': 'SN', '🇸🇴': 'SO', '🇸🇷': 'SR', '🇸🇸': 'SS', '🇸🇹': 'ST', '🇸🇻': 'EV', '🇸🇽': 'SX', 
        '🇸🇾': 'SY', '🇸🇿': 'SZ', '🇹🇦': 'TA', '🇹🇨': 'TC', '🇹🇩': 'TD', '🇹🇫': 'TF', '🇹🇬': 'TG', 
        '🇹🇭': 'TH', '🇹🇯': 'TJ', '🇹🇰': 'TK', '🇹🇱': 'TL', '🇹🇲': 'TM', '🇹🇳': 'TN', '🇹🇴': 'TO', 
        '🇹🇷': 'TR', '🇹🇹': 'TT', '🇹🇻': 'TV', '🇹🇼': 'TW', '🇹🇿': 'TZ', '🇺🇦': 'UA', '🇺🇬': 'UG', 
        '🇺🇲': 'UM', '🇺🇳': 'UN', '🇺🇸': 'US', '🇺🇾': 'UY', '🇺🇿': 'UZ', '🇻🇦': 'VA', '🇻🇨': 'VC', 
        '🇻🇪': 'VE', '🇻🇬': 'VG', '🇻🇮': 'VI', '🇻🇳': 'VN', '🇻🇺': 'VU', '🇼🇫': 'WF', '🇼🇸': 'WS', 
        '🇽🇰': 'XK', '🇾🇪': 'YE', '🇾🇹': 'YT', '🇿🇦': 'ZA', '🇿🇲': 'ZM', '🇿🇼': 'ZW'
    }

    EMOJI_NUMBERS = [
        u'\u0030\u20E3',
        u'\u0031\u20E3',
        u'\u0032\u20E3',
        u'\u0033\u20E3',
        u'\u0034\u20E3',
        u'\u0035\u20E3',
        u'\u0036\u20E3',
        u'\u0037\u20E3',
        u'\u0038\u20E3',
        u'\u0039\u20E3',
        u'\U0001F51F'
    ]

    @staticmethod
    def trans(key, *args):
        """"""
        translated = translations[Config.lang][key]
        if args:
            return translated.format(*args)

        return translated

    @staticmethod
    def clear_messages(messages, timer=15):
        """"""
        cb = partial(delete_msgs, messages)
        Timer(timer, cb)

    @staticmethod
    def generate_leaderboard_img(playerstats, season=None):
        """"""
        img = Image.open(TEMPLATES_DIR + "/leaderboard.png")
        font = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 25)
        fontbig = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 28)
        draw = ImageDraw.Draw(img)

        draw.text((1, 45), align_text(
            f'Season: {season.name}' if season else 'General Stats', 130), font=fontbig)

        for idx, p in enumerate(playerstats):
            draw.text((73, 235+65*idx), str(p.name)[:18], font=font)
            draw.text((340, 235+65*idx), str(p.kills), font=font)
            draw.text((500, 235+65*idx), str(p.deaths), font=font)
            draw.text((660, 235+65*idx), str(p.played), font=font)
            draw.text((820, 235+65*idx), str(p.wins), font=font)
            draw.text((980, 235+65*idx), str(p.rating), font=font)

        img.save(SAVE_IMG_DIR + '/leaderboard.png')
        return File(SAVE_IMG_DIR + '/leaderboard.png')

    @staticmethod
    def generate_statistics_img(stats, season=None):
        """"""
        img = Image.open(TEMPLATES_DIR + "/statistics.png")
        font = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 25)
        draw = ImageDraw.Draw(img)
        fontbig = ImageFont.truetype(FONTS_DIR + "/ARIALUNI.TTF", 28)

        draw.text((1, 40), align_text(
            f'Season: {season.name}' if season else 'General Stats', 55), font=fontbig)

        draw.text((1, 90), align_text(stats.name[:14], 55), font=fontbig)

        draw.text((46, 226+109*0), align_text(str(stats.kills), 14), font=font)
        draw.text((46, 226+109*1), align_text(str(stats.deaths), 14), font=font)
        draw.text((46, 226+109*2), align_text(str(stats.assists), 14), font=font)
        draw.text((46, 226+109*3), align_text(str(stats.kdr), 14), font=font)
        draw.text((46, 226+109*4), align_text(str(stats.headshots), 14), font=font)

        draw.text((365, 226+109*0), align_text(f'{stats.hsp}%', 20), font=font)
        draw.text((365, 226+109*1),
                  align_text(str(stats.played), 20), font=font)
        draw.text((365, 226+109*2), align_text(str(stats.wins), 20), font=font)
        draw.text((365, 226+109*3),
                  align_text(f'{stats.win_percent}%', 20), font=font)
        draw.text((365, 226+109*4), align_text(str(stats.rating), 20), font=font)

        img.save(SAVE_IMG_DIR + '/statistics.png')
        return File(SAVE_IMG_DIR + '/statistics.png')
