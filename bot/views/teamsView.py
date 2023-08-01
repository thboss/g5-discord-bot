# teamsView.py

from discord import Interaction, Member, Message, ButtonStyle, Embed
from discord.ui import View, Button
from random import shuffle
from typing import List

from bot.helpers.api import api


class PlayerButton(Button['PickTeamsView']):
    def __init__(self, user: Member):
        super().__init__(label=user.display_name, style=ButtonStyle.secondary)
        self.user = user

    async def callback(self, interaction: Interaction):
        await self.view.on_click_button(interaction, self)


class PickTeamsView(View):
    def __init__(self, message: Message, users: List[Member], timeout=180):
        super().__init__(timeout=timeout)
        self.players_buttons = [PlayerButton(user) for user in users]
        for button in self.players_buttons:
            self.add_item(button)

        self.message = message
        self.users = users
        self.pick_order = '1' + '2211' * 20
        self.pick_number = 0
        self.users_left = users.copy()
        self.teams = [[], []]
        self.future = None

    @property
    def _active_picker(self):
        try:
            picking_team_number = int(self.pick_order[self.pick_number])
            picking_team = self.teams[picking_team_number - 1]
            return picking_team[0] if picking_team else None
        except IndexError:
            return None

    def _pick_player(self, captain: Member, selected_player: Member):
        if captain == selected_player:
            return False

        if not self.teams[0]:
            picking_team = self.teams[0]
            self.users_left.remove(captain)
            picking_team.append(captain)
        elif self.teams[1] == [] and captain in self.teams[0]:
            return False
        elif not self.teams[1]:
            picking_team = self.teams[1]
            self.users_left.remove(captain)
            picking_team.append(captain)
        elif captain == self.teams[0][0]:
            picking_team = self.teams[0]
        elif captain == self.teams[1][0]:
            picking_team = self.teams[1]
        else:
            return False

        if captain != self._active_picker or len(picking_team) > len(self.users) // 2:
            return False

        self.users_left.remove(selected_player)
        picking_team.append(selected_player)
        self.pick_number += 1
        return True

    async def on_click_button(self, interaction: Interaction, button: PlayerButton):
        await interaction.response.defer()
        captain = interaction.user
        selected_player = button.user
        print('captain', captain)
        print('selected player', selected_player)

        if selected_player is None or selected_player not in self.users_left or captain not in self.users:
            return
        
        print('here')

        if not self._pick_player(captain, selected_player):
            print('not _pick_player')
            return

        self._remove_captain_button(captain)

        title = f"Team **{captain.display_name}** picked **{selected_player.display_name}**"

        if not self.users_left:
            embed = self.create_teams_embed(title)
            await self.message.edit(embed=embed, view=None)
            self.stop()
            return

        self.remove_item(button)
        embed = self.create_teams_embed(title)
        await self.message.edit(embed=embed, view=self)

    def _remove_captain_button(self, captain: Member):
        captain_button = next(
            (btn for btn in self.players_buttons if btn.user == captain), None)
        if captain_button:
            self.remove_item(captain_button)

    def create_teams_embed(self, title: str):
        embed = Embed(title=title)
        self.add_team_fields(embed)
        if self.users_left:
            self.add_players_left_field(embed)
            self.add_captains_info_field(embed)
        return embed

    def add_team_fields(self, embed: Embed):
        for idx, team in enumerate(self.teams, start=1):
            team_name = f'__Team {idx}__'
            team_players = "*Empty*" if len(
                team) == 0 else '\n'.join(u.mention for u in team)
            embed.add_field(name=team_name, value=team_players)

    def add_players_left_field(self, embed: Embed):
        users_left_str = '\n'.join(user.mention for user in self.users if not any(
            user in team for team in self.teams))
        embed.insert_field_at(1, name="Players Left", value=users_left_str)

    def add_captains_info_field(self, embed: Embed):
        status_str = ''
        status_str += f'Team1 captain: {self.teams[0][0].mention}\n' if len(
            self.teams[0]) else 'Team1 captain:\n'
        status_str += f'Team2 captain: {self.teams[1][0].mention}\n\n' if len(
            self.teams[1]) else 'Team2 captain:\n\n'
        status_str += f'Choice: {self._active_picker.mention}' if self._active_picker is not None else 'Choice:'
        embed.add_field(name="Captains Info", value=status_str)

    async def start(self, captain_method: str):
        if captain_method == 'rank':
            try:
                leaderboard = await api.get_leaderboard(self.users)
            except Exception as e:
                captain_method = 'random'
            else:
                stats_dict = dict(zip(leaderboard, self.users))
                players_stats = list(stats_dict.keys())
                players_stats.sort(key=lambda x: x.rating)

                for team in self.teams:
                    player_stat = players_stats.pop()
                    captain = stats_dict.get(player_stat)
                    self.users_left.remove(captain)
                    team.append(captain)
                    self._remove_captain_button(captain)

        if captain_method == 'random':
            temp_users = self.users_left.copy()
            shuffle(temp_users)

            for team in self.teams:
                captain = temp_users.pop()
                self.users_left.remove(captain)
                team.append(captain)
                self._remove_captain_button(captain)

        if not self.users_left:
            self.stop()
