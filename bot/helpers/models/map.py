# bot/helpers/models/map.py

from typing import Literal


class MapModel:
    """"""

    def __init__(
        self,
        display_name: str,
        dev_name: str,
        game_mode: Literal["competitive", "wingman"],
        map_id=None,
    ):
        """"""
        self.display_name = display_name
        self.dev_name = dev_name
        self.game_mode = game_mode
        self.map_id = map_id

    def __eq__(self, other):
        if (isinstance(other, MapModel)):
            return self.dev_name == other.dev_name
        return False

    @classmethod
    def from_dict(cls, data: dict) -> "MapModel":
        """"""
        return cls(
            data['display_name'],
            data['dev_name'],
            data['game_mode'],
            map_id=data['map_id']
        )
