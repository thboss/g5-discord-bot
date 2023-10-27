"""

"""

from yoyo import step

__depends__ = {'20211226_01_aVejE-create-base-tables'}

steps = [
    step(
      (
        'ALTER TABLE guilds\n'
        '    ADD COLUMN dathost_email VARCHAR(255) DEFAULT NULL,\n'
        '    ADD COLUMN dathost_password VARCHAR(255) DEFAULT NULL\n'
        ';'
      ),
      (
        'ALTER TABLE guilds\n'
        '    DROP COLUMN dathost_email,\n'
        '    DROP COLUMN dathost_password\n'
        ';'
      )
    )
]
