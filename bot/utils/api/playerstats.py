
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from ...resources import Sessions, Config
from ..utils import Utils


class PlayerStats:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.steam = data["steam"]
        self.name = data["name"]
        self.score = data["score"]
        self.kills = data["kills"]
        self.deaths = data["deaths"]
        self.assists = data["assists"]
        self.suicides = data["suicides"]
        self.tk = data["tk"]
        self.shots = data["shots"]
        self.hits = data["hits"]
        self.headshots = data["headshots"]
        self.connected = data["connected"]
        self.rounds_tr = data["rounds_tr"]
        self.rounds_ct = data["rounds_ct"]
        self.knife = data["knife"]
        self.glock = data["glock"]
        self.hkp2000 = data["hkp2000"]
        self.usp_silencer = data["usp_silencer"]
        self.p250 = data["p250"]
        self.deagle = data["deagle"]
        self.elite = data["elite"]
        self.fiveseven = data["fiveseven"]
        self.tec9 = data["tec9"]
        self.cz75a = data["cz75a"]
        self.revolver = data["revolver"]
        self.nova = data["nova"]
        self.xm1014 = data["xm1014"]
        self.mag7 = data["mag7"]
        self.sawedoff = data["sawedoff"]
        self.bizon = data["bizon"]
        self.mac10 = data["mac10"]
        self.mp9 = data["mp9"]
        self.mp7 = data["mp7"]
        self.ump45 = data["ump45"]
        self.p90 = data["p90"]
        self.galilar = data["galilar"]
        self.ak47 = data["ak47"]
        self.scar20 = data["scar20"]
        self.famas = data["famas"]
        self.m4a1 = data["m4a1"]
        self.m4a1_silencer = data["m4a1_silencer"]
        self.aug = data["aug"]
        self.ssg08 = data["ssg08"]
        self.sg556 = data["sg556"]
        self.awp = data["awp"]
        self.g3sg1 = data["g3sg1"]
        self.m249 = data["m249"]
        self.negev = data["negev"]
        self.hegrenade = data["hegrenade"]
        self.flashbang = data["flashbang"]
        self.smokegrenade = data["smokegrenade"]
        self.inferno = data["inferno"]
        self.decoy = data["decoy"]
        self.taser = data["taser"]
        self.mp5sd = data["mp5sd"]
        self.breachcharge = data["breachcharge"]
        self.head = data["head"]
        self.chest = data["chest"]
        self.stomach = data["stomach"]
        self.left_arm = data["left_arm"]
        self.right_arm = data["right_arm"]
        self.left_leg = data["left_leg"]
        self.right_leg = data["right_leg"]
        self.c4_planted = data["c4_planted"]
        self.c4_exploded = data["c4_exploded"]
        self.c4_defused = data["c4_defused"]
        self.ct_win = data["ct_win"]
        self.tr_win = data["tr_win"]
        self.hostages_rescued = data["hostages_rescued"]
        self.vip_killed = data["vip_killed"]
        self.vip_escaped = data["vip_escaped"]
        self.vip_played = data["vip_played"]
        self.mvp = data["mvp"]
        self.damage = data["damage"]
        self.match_win = data["match_win"]
        self.match_draw = data["match_draw"]
        self.match_lose = data["match_lose"]
        self.first_blood = data["first_blood"]
        self.no_scope = data["no_scope"]
        self.no_scope_dis = data["no_scope_dis"]

    @property
    def win_percent(self):
        """"""
        total_matches = self.match_win + self.match_draw + self.match_lose
        return f'{self.match_win / total_matches * 100:.2f}' if total_matches else '0.00'

    @property
    def kdr(self):
        """"""
        return f'{self.kills / self.deaths:.2f}' if self.deaths else '0.00'

    @property
    def hsp(self):
        """"""
        return f'{self.headshots / self.kills * 100:.2f}' if self.kills else '0.00'

    @property
    def total_matches(self):
        """"""
        return self.match_draw + self.match_win + self.match_lose

    @classmethod
    async def get_player_stats(cls, db_user, season_id=None):
        """"""
        url = f"{Config.api_url}/ranks/{db_user.steam}/"
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
    async def get_leaderboard(cls, users, season_id=None):
        """"""
        url = f"{Config.api_url}/ranks/"
        if season_id:
            url += f"season/{season_id}"

        db_steam_ids = [usr.steam for usr in users]

        try:
            async with Sessions.requests.get(url=url) as resp:
                resp_data = await resp.json()
                if resp.status >= 400:
                    raise Exception('Response: ' + resp_data['message'])
                players = list(
                    filter(lambda x: x['steam'] in db_steam_ids, resp_data))
                api_steam_ids = [player['steam'] for player in players]
                api_steam_ids = list(filter(lambda x: x in db_steam_ids, api_steam_ids))

                for steam_id in db_steam_ids:
                    if steam_id not in api_steam_ids:
                        api_steam_ids.append(steam_id)
                        players.append({
                            "steam": steam_id,
                            "score": 1000,
                            "kills": 0,
                            "deaths": 0,
                            "assists": 0,
                            "suicides": 0,
                            "tk": 0,
                            "shots": 0,
                            "hits": 0,
                            "headshots": 0,
                            "connected": 0,
                            "rounds_tr": 0,
                            "rounds_ct": 0,
                            "knife": 0,
                            "glock": 0,
                            "hkp2000": 0,
                            "usp_silencer": 0,
                            "p250": 0,
                            "deagle": 0,
                            "elite": 0,
                            "fiveseven": 0,
                            "tec9": 0,
                            "cz75a": 0,
                            "revolver": 0,
                            "nova": 0,
                            "xm1014": 0,
                            "mag7": 0,
                            "sawedoff": 0,
                            "bizon": 0,
                            "mac10": 0,
                            "mp9": 0,
                            "mp7": 0,
                            "ump45": 0,
                            "p90": 0,
                            "galilar": 0,
                            "ak47": 0,
                            "scar20": 0,
                            "famas": 0,
                            "m4a1": 0,
                            "m4a1_silencer": 0,
                            "aug": 0,
                            "ssg08": 0,
                            "sg556": 0,
                            "awp": 0,
                            "g3sg1": 0,
                            "m249": 0,
                            "negev": 0,
                            "hegrenade": 0,
                            "flashbang": 0,
                            "smokegrenade": 0,
                            "inferno": 0,
                            "decoy": 0,
                            "taser": 0,
                            "mp5sd": 0,
                            "breachcharge": 0,
                            "head": 0,
                            "chest": 0,
                            "stomach": 0,
                            "left_arm": 0,
                            "right_arm": 0,
                            "left_leg": 0,
                            "right_leg": 0,
                            "c4_planted": 0,
                            "c4_exploded": 0,
                            "c4_defused": 0,
                            "ct_win": 0,
                            "tr_win": 0,
                            "hostages_rescued": 0,
                            "vip_killed": 0,
                            "vip_escaped": 0,
                            "vip_played": 0,
                            "mvp": 0,
                            "damage": 0,
                            "match_win": 0,
                            "match_draw": 0,
                            "match_lose": 0,
                            "first_blood": 0,
                            "no_scope": 0,
                            "no_scope_dis": 0
                        })

                players.sort(key=lambda x: db_steam_ids.index(x['steam']))
                for i, p in enumerate(players):
                    p['name'] = users[i].user.display_name

                return [cls(player) for player in players]
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))

    @staticmethod
    async def reset_stats(headers, steam_id):
        """"""
        url = f"{Config.api_url}/ranks/{steam_id}"

        try:
            async with Sessions.requests.delete(url=url, headers=headers) as resp:
                if resp.status >= 400:
                    resp_data = await resp.json()
                    raise Exception('Response: ' + resp_data['message'])
                return True
        except ContentTypeError:
            raise Exception(Utils.trans('invalid-api-key'))
        except (ClientConnectionError, TimeoutError):
            raise Exception(Utils.trans('connect-api-error'))
