# bot/helpers/models/map.py


class MapModel:
    """"""

    def __init__(
        self,
        display_name: str,
        dev_name: str,
        map_id=None,
    ):
        """"""
        self.display_name = display_name
        self.dev_name = dev_name
        self.map_id = map_id

    def __eq__(self, other):
        if (isinstance(other, MapModel)):
            return self.dev_name == other.dev_name
        return False

    @classmethod
    def from_dict(cls, data: dict) -> "MapModel":
        """"""
        display_name = data['display_name']
        dev_name = data['dev_name']
        map_id = data['map_id']

        return cls(
            display_name,
            dev_name,
            map_id=map_id
        )
