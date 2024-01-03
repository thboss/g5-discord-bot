# bot/helpers/models/playerstats.py


class PlayerStatsModel:
    """"""

    def __init__(
        self,
        match_id: str,
        user_id: int,
        team: str,
        kills: int,
        deaths: int,
        assists: int,
        mvps: int,
        headshots: int,
        k2: int,
        k3: int,
        k4: int,
        k5: int,
        score: int
    ):
        """"""
        self.match_id = match_id
        self.user_id = user_id
        self.team = team
        self.kills = kills
        self.deaths = deaths
        self.assists = assists
        self.mvps = mvps
        self.headshots = headshots
        self.k2 = k2
        self.k3 = k3
        self.k4 = k4
        self.k5 = k5
        self.score = score

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
            data['match_id'],
            data['user_id'],
            data['team'],
            data['kills'],
            data['deaths'],
            data['assists'],
            data['mvps'],
            data['headshots'],
            data['k2'],
            data['k3'],
            data['k4'],
            data['k5'],
            data['score']
        )
