"""

"""

from yoyo import step

__depends__ = {'20231102_01_5xafK'}

steps = [
    step(
      (
        'ALTER TABLE lobbies\n'
        '    ADD COLUMN connect_time INTEGER DEFAULT 300\n'
        ';'
      ),
      (
        'ALTER TABLE lobbies\n'
        '    DROP COLUMN connect_time\n'
        ';'
      )
    )
]
