"""

"""

from yoyo import step

__depends__ = {'20231105_01_HG1Zt'}

steps = [
    step(
      (
        'ALTER TABLE lobbies\n'
        '    ADD COLUMN location VARCHAR(32) DEFAULT NULL\n'
        ';'
      ),
      (
        'ALTER TABLE lobbies\n'
        '    DROP COLUMN location\n'
        ';'
      )
    )
]
