"""

"""

from yoyo import step

__depends__ = {'20211226_01_aVejE-create-base-tables'}

steps = [
    step(
      (
        'CREATE TABLE user_stats(\n)'
        '    user_id BIGINT REFERENCES users (discord_id),\n'
        '    kills INTEGER DEFAULT 0,\n'
        '    deaths INTEGER DEFAULT 0,\n'
        '    assists INTEGER DEFAULT 0,\n'
        '    wins INTEGER DEFAULT 0,\n'
        '    played_matches INTEGER DEFAULT 0,\n'
        '    elo INTEGER DEFAULT 1000\n'
        ';'
      ),
      'DROP TABLE user_stats'
    )
]
