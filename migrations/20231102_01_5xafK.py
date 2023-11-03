"""

"""

from yoyo import step

__depends__ = {'20231027_01_8qLPt'}

steps = [
    step(
      (
        'ALTER TABLE matches\n'
        '    ADD COLUMN api_key VARCHAR(32) DEFAULT NULL\n'
        ';'
      ),
      (
        'ALTER TABLE matches\n'
        '    DROP COLUMN api_key\n'
        ';'
      )
    )
]
