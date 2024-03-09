# bot/helpers/models/playerstats.py


class PlayerStatsModel:
    """"""

    def __init__(
        self,
        user_id: int,
        steam_id: int,
        kills: int,
        deaths: int,
        assists: int,
        mvps: int,
        headshots: int,
        k2: int,
        k3: int,
        k4: int,
        k5: int,
        wins: int,
        total_matches: int
    ):
        """"""
        self.user_id = user_id
        self.steam_id = steam_id
        self.kills = kills
        self.deaths = deaths
        self.assists = assists
        self.mvps = mvps
        self.headshots = headshots
        self.k2 = k2
        self.k3 = k3
        self.k4 = k4
        self.k5 = k5
        self.wins = wins
        self.total_matches = total_matches

    @property
    def kdr(self):
        return round(self.kills / self.deaths, 2) if self.deaths else 0.00
    
    @property
    def hsp(self):
        return round(self.headshots / self.kills, 2) * 100 if self.kills else 0.00

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerStatsModel":
        """"""
        return cls(
            data['user_id'],
            data['steam_id'],
            data['kills'],
            data['deaths'],
            data['assists'],
            data['mvps'],
            data['headshots'],
            data['k2'],
            data['k3'],
            data['k4'],
            data['k5'],
            data['wins'],
            data['total_matches']
        )
