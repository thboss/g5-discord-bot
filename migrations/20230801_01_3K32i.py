"""
Add column 'game_mode' in tabel 'guild_maps'
"""

from yoyo import step

__depends__ = {'20230729_01_hno5l'}

steps = [
    step(
        (
            'ALTER TABLE guild_maps\n'
            '    ADD COLUMN game_mode game_mode DEFAULT \'competitive\'\n'
            ';'
        ),
        (
            'ALTER TABLE guild_maps\n'
            '    DROP COLUMN game_mode\n'
            ';'
        ),
    )
]

