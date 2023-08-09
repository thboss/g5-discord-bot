# G5 Bot

A Discord bot to manage CS:GO PUGs and teams matches. Connects to [G5API](https://github.com/PhlexPlexico/G5API).

## Setup

1. First you must have a bot instance to run this script on. Follow Discord's tutorial [here](https://discord.onl/2019/03/21/how-to-set-up-a-bot-application/) on how to set one up.

   - The required permissions is `1360325712`.
   - Enable the "server members intent" for your bot, as shown [here](https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents).

2. Install libpq-dev (Linux only?). This is needed to install the psycopg2 Python package.

   - Linux command is `sudo apt-get install libpq-dev`.

3. Run `pip3 install -r requirements.txt` in the repository's root directory to get the necessary libraries.

4. Install PostgreSQL 9.5 or higher.

   - Linux command is `sudo apt-get install postgresql`.
   - Windows users can download [here](https://www.postgresql.org/download/windows).

5. Run the psql tool with `sudo -u postgres psql` and create a database by running the following commands:

   ```sql
   CREATE ROLE "g5" WITH LOGIN PASSWORD 'yourpassword';
   CREATE DATABASE "g5" OWNER g5;
   ```

   Be sure to replace `'yourpassword'` with your own desired password.

   Quit psql with `\q`

6. Modify `config.json`.

7. Apply the database migrations by running `python3 migrate.py up`.

8. Run the launcher Python script by running, `python3 run.py`.

## Thanks To

[Cameron Shinn](https://github.com/cameronshinn) for his initial implementation of [csgo-league-bot](https://github.com/csgo-league/csgo-league-bot).
[PhlexPlexico](https://github.com/PhlexPlexico/) for his implementation of [G5API](https://github.com/PhlexPlexico/G5API)
