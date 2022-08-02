from ..utils import Utils
from ..resources import G5, Config
from datetime import datetime


class Embeds:
    """"""

    @staticmethod
    def ready(users, reactors):
        """"""
        str_value = ''
        embed = G5.bot.embed_template(
            title=Utils.trans('lobby-filled-up'))

        for num, user in enumerate(users, start=1):
            if user not in reactors:
                str_value += f':heavy_multiplication_x:  {num}. {user.mention}\n '
            else:
                str_value += f'✅  {num}. {user.mention}\n '

        embed.add_field(name=f":hourglass: __{Utils.trans('players')}__",
                        value='-------------------\n' + str_value)
        embed.set_footer(text=Utils.trans('react-ready', '✅'))
        return embed

    @staticmethod
    def map_pool(active_maps, inactive_maps):
        """"""
        embed = G5.bot.embed_template(title=Utils.trans('map-pool'))

        active_maps = ''.join(
            f'{emoji}  `{m.display_name}`\n' for emoji, m in active_maps.items())
        inactive_maps = ''.join(
            f'{emoji}  `{m.display_name}`\n' for emoji, m in inactive_maps.items())

        if not inactive_maps:
            inactive_maps = Utils.trans("none")

        if not active_maps:
            active_maps = Utils.trans("none")

        embed.add_field(name=Utils.trans(
            "active-maps"), value=active_maps)
        embed.add_field(name=Utils.trans(
            "inactive-maps"), value=inactive_maps)
        embed.set_footer(text=Utils.trans('map-pool-footer'))
        return embed

    @staticmethod
    def pick_teams(teams, pick_emojis, active_picker, title):
        """"""
        embed = G5.bot.embed_template(title=title)

        for team in teams:
            team_name = f'__{Utils.trans("match-team")}__' if len(
                team) == 0 else f'__{Utils.trans("match-team", team[0].display_name)}__'

            if len(team) == 0:
                team_players = Utils.trans("team-empty")
            else:
                team_players = '\n'.join(p.display_name for p in team)

            embed.add_field(name=team_name, value=team_players)

        users_left_str = ''

        for index, (emoji, user) in enumerate(pick_emojis.items()):
            if not any(user in team for team in teams):
                users_left_str += f'{emoji}  {user.mention}\n'
            else:
                users_left_str += f':heavy_multiplication_x:  ~~{user.mention}~~\n'

        embed.insert_field_at(1, name=Utils.trans(
            "players-left"), value=users_left_str)

        status_str = ''

        status_str += f'{Utils.trans("capt1", teams[0][0].mention)}\n' if len(
            teams[0]) else f'{Utils.trans("capt1")}\n '

        status_str += f'{Utils.trans("capt2", teams[1][0].mention)}\n\n' if len(
            teams[1]) else f'{Utils.trans("capt2")}\n\n '

        status_str += Utils.trans("current-capt", active_picker.mention) \
            if active_picker is not None else Utils.trans("current-capt")

        embed.add_field(name=Utils.trans("info"), value=status_str)
        embed.set_footer(text=Utils.trans('team-pick-footer'))
        return embed

    @staticmethod
    def veto_maps(title, method, series, mpool, maps_pick, maps_ban, ban_number, ban_order, captains, active_picker):
        """"""
        title += f' ({series.upper()})'
        embed = G5.bot.embed_template(title=title)
        maps_str = ''

        for m in mpool:
            if m in maps_pick:
                maps_str += f'✅ {m.emoji}  {m.display_name}\n'
            elif m in maps_ban:
                maps_str += f'❌ {m.emoji}  ~~{m.display_name}~~\n'
            else:
                maps_str += f'❔ {m.emoji}  {m.display_name}\n'

        embed.add_field(name=Utils.trans("maps-left"), value=maps_str)
        if ban_number < len(ban_order):
            status_str = ''
            status_str += Utils.trans("capt1",
                                      captains[0].mention) + '\n'
            status_str += Utils.trans("capt2",
                                      captains[1].mention) + '\n\n'
            status_str += Utils.trans("current-capt",
                                      active_picker.mention) + '\n'
            status_str += Utils.trans('map-method', method)
            embed.add_field(name=Utils.trans("info"), value=status_str)

        embed.set_footer(text=Utils.trans('map-veto-footer'))
        return embed

    @staticmethod
    def match_info(api_match, game_server=None, mapstats=[]):
        """"""
        title = f"**{api_match.team1_string}**  [{api_match.team1_score}:{api_match.team2_score}]  **{api_match.team2_string}**"
        description = ''

        if game_server:
            description += game_server.connect_info

        for mapstat in mapstats:
            if mapstat.start_time:
                start_time = datetime.fromisoformat(
                    mapstat.start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")

                description += f"**{Utils.trans('map')} {mapstat.map_number+1}:** {mapstat.map_name}\n" \
                    f"**{Utils.trans('score')}:** {api_match.team1_string}  [{mapstat.team1_score}:{mapstat.team2_score}]  " \
                    f"{api_match.team2_string}\n**{Utils.trans('start-time')}:** {start_time}\n"

            if mapstat.end_time:
                end_time = datetime.fromisoformat(
                    mapstat.end_time.replace("Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")
                description += f"**{Utils.trans('end-time')}:** {end_time}\n"
            description += '\n\n'

        if Config.g5v_url:
            description += f"[{Utils.trans('more-info')}]({Config.g5v_url}/match/{api_match.id})"

        embed = G5.bot.embed_template(title=title, description=description)
        embed.set_author(name=f"{'🔴' if api_match.end_time else '🟢'} {Utils.trans('match-id', api_match.id)}")
        if not mapstats and not api_match.end_time:
            embed.set_footer(text=Utils.trans('match-info-footer'))
        return embed

    @staticmethod
    def pug_queue(lobby, title, queued_users):
        """"""
        if title:
            embed = G5.bot.embed_template(title=title)
        else:
            embed = G5.bot.embed_template()

        queued_players_str = Utils.trans(
            'lobby-is-empty') if not queued_users else ""
        for num, user in enumerate(queued_users, start=1):
            queued_players_str += f'{num}. {user.mention}\n'

        embed.add_field(
            name=f"{Utils.trans('joined-players')} `({len(queued_users)}/{lobby.capacity})`:",
            value=queued_players_str
        )

        return embed

    @staticmethod
    def teams_queue(lobby, title, team1, team2, team1_users, team2_users):
        """"""
        if title:
            embed = G5.bot.embed_template(title=title)
        else:
            embed = G5.bot.embed_template()

        team1_name = team1.name if team1 else Utils.trans("none")
        team2_name = team2.name if team2 else Utils.trans("none")
        team1_players_str = Utils.trans(
            'no-players-joined') if not team1_users else ""
        team2_players_str = Utils.trans(
            'no-players-joined') if not team2_users else ""

        for num, user in enumerate(team1_users, start=1):
            team1_players_str += f"{num}. {user.mention} {'`👑`' if user == team1.captain else ''}\n"

        for num, user in enumerate(team2_users, start=1):
            team2_players_str += f"{num}. {user.mention} {'`👑`' if user == team2.captain else ''}\n"

        embed.add_field(
            name=f"{Utils.trans('team1-name', team1_name)} `({len(team1_users)}/{int(lobby.capacity/2)})`",
            value=team1_players_str
        )

        embed.add_field(
            name=f"{Utils.trans('team2-name', team2_name)} `({len(team2_users)}/{int(lobby.capacity/2)})`",
            value=team2_players_str
        )

        return embed

    @staticmethod
    def lobby_info(lobby, active_maps):
        """"""
        embed = G5.bot.embed_template()
        embed.set_author(name=Utils.trans('lobby-title', lobby.id))

        embed.add_field(
            name='Type',
            value='PUG' if lobby.pug else 'Teams',
            inline=False
        )
        embed.add_field(
            name='Capacity',
            value=lobby.capacity,
            inline=False
        )
        embed.add_field(
            name='Region',
            value=lobby.region or 'Any',
            inline=False
        )
        embed.add_field(
            name='Best of',
            value=lobby.series[2] + ' Maps',
            inline=False
        )
        if lobby.pug:
            embed.add_field(
                name='Teams selection',
                value=lobby.team_method,
                inline=False
            )
            if lobby.team_method == 'captains':
                embed.add_field(
                    name='Captains selection',
                    value=lobby.captain_method,
                    inline=False
                )
        embed.add_field(
            name='Map Pool',
            value=''.join(str(m.emoji) for m in active_maps),
            inline=False
        )

        return embed
