# lobby.py

from asyncpg.exceptions import UniqueViolationError
from typing import List, Optional
from collections import defaultdict
import asyncio

from discord.ext import commands
from discord import app_commands, Interaction, Embed, Member, VoiceState, HTTPException, VoiceChannel, SelectOption

from bot.helpers.db import db
from bot.helpers.api import api
from bot.helpers.models import LobbyModel
from bot.helpers.errors import CustomError, JoinLobbyError
from bot.views import ReadyView, DropDownView
from bot.bot import G5Bot
from bot.helpers.utils import COUNTRY_FLAGS


CAPACITY_CHOICES = [
    app_commands.Choice(name="1vs1", value=2),
    app_commands.Choice(name="2vs2", value=4),
    app_commands.Choice(name="3vs3", value=6),
    app_commands.Choice(name="4vs4", value=8),
    app_commands.Choice(name="5vs5", value=10),
    app_commands.Choice(name="6vs6", value=12),
]

TEAM_SELECTION_CHOICES = [
    app_commands.Choice(name="Random", value="random"),
    app_commands.Choice(name="Auto balance", value="autobalance"),
    app_commands.Choice(name="Captains", value="captains"),
]

CAPTAIN_SELECTION_CHOICES = [
    app_commands.Choice(name="Random", value="random"),
    app_commands.Choice(name="Rank", value="rank"),
    app_commands.Choice(name="Volunteer", value="volunteer"),
]

MAP_SELECTION_CHOICES = [
    app_commands.Choice(name="Random", value="random"),
    app_commands.Choice(name="Veto", value="veto"),
]

AUTO_READY_CHOICES = [
    app_commands.Choice(name="ON", value=True),
    app_commands.Choice(name="OFF", value=False)
]

SERIES_CHOICES = [
    app_commands.Choice(name="Bo1", value="bo1"),
    app_commands.Choice(name="Bo2", value="bo2"),
    app_commands.Choice(name="Bo3", value="bo3")
]

GAME_MODE_CHOICES = [
    app_commands.Choice(name="Competitive", value="competitive"),
    app_commands.Choice(name="Wingman", value="wingman")
]


class LobbyCog(commands.Cog, name="Lobby"):
    """"""

    def __init__(self, bot: G5Bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.awaiting = {}
        self.awaiting = defaultdict(lambda: False, self.awaiting)

    @app_commands.command(
        name='create-lobby',
        description='Create a new lobby.'
    )
    @app_commands.describe(
        capacity="Capacity of the lobby",
        teams_method="Teams selection method",
        captains_method="Captains selection method",
        map_method="Map selection method",
        series="Number of maps per match",
        game_mode="Set game mode",
        region="Game server location where the match must setup. e.g. US"
    )
    @app_commands.choices(
        capacity=CAPACITY_CHOICES,
        teams_method=TEAM_SELECTION_CHOICES,
        captains_method=CAPTAIN_SELECTION_CHOICES,
        map_method=MAP_SELECTION_CHOICES,
        series=SERIES_CHOICES,
        game_mode=GAME_MODE_CHOICES,
        auto_ready=AUTO_READY_CHOICES
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_lobby(
        self,
        interaction: Interaction,
        capacity: app_commands.Choice[int],
        teams_method: app_commands.Choice[str],
        captains_method: app_commands.Choice[str],
        map_method: app_commands.Choice[str],
        series: app_commands.Choice[str],
        game_mode: app_commands.Choice[str],
        auto_ready: app_commands.Choice[int],
        season_id: Optional[int],
        region: Optional[str],
    ):
        """ Create a new lobby. """
        await interaction.response.defer(ephemeral=True)
        if region and region.upper() not in COUNTRY_FLAGS:
            raise CustomError("Invalid region code")
        
        if season_id:
            season = await api.get_season(season_id)
            if not season:
                raise CustomError("Invalid season ID")

        guild = interaction.guild
        guild_model = await db.get_guild_by_id(guild.id, self.bot)
        category = await guild.create_category(name="Lobby")
        text_channel = await guild.create_text_channel(category=category, name='Queue')
        voice_channel = await guild.create_voice_channel(
            category=category,
            name='Lobby',
            user_limit=capacity.value)

        await text_channel.set_permissions(guild.self_role, send_messages=True)
        await voice_channel.set_permissions(guild.self_role, connect=True)
        await text_channel.set_permissions(guild.default_role, send_messages=False)
        await voice_channel.set_permissions(guild.default_role, connect=False)
        await voice_channel.set_permissions(guild_model.linked_role, connect=True)

        lobby_data = {
            'guild': guild.id,
            'capacity': capacity.value,
            'team_method': teams_method.value,
            'captain_method': captains_method.value,
            'map_method': map_method.value,
            'autoready': auto_ready.value,
            'series_type': series.value,
            'game_mode': game_mode.value,
            'category': category.id,
            'queue_channel': text_channel.id,
            'lobby_channel': voice_channel.id
        }
        if region:
            lobby_data['region'] = region.upper()
        if season_id:
            lobby_data['season_id'] = season_id

        lobby_id = await db.insert_lobby(lobby_data)

        await category.edit(name=f"Lobby #{lobby_id}")

        guild_maps = await db.get_guild_maps(guild, game_mode.value)
        lobby_model = await db.get_lobby_by_id(lobby_id, self.bot)
        await db.insert_lobby_maps(lobby_id, guild_maps[:7])

        await self.update_queue_msg(lobby_model)

        embed = Embed(
            description=f"Lobby #{lobby_id} created successfully.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name='delete-lobby',
        description='delete the provided lobby.'
    )
    @app_commands.describe(lobby_id="Lobby ID.")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_lobby(self, interaction: Interaction, lobby_id: int):
        """"""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        lobby_model = await db.get_lobby_by_id(lobby_id, self.bot)
        if not lobby_model:
            raise CustomError("Invalid Lobby ID")

        if lobby_model.guild.id != guild.id:
            raise CustomError("This lobby was not created in this server.")

        if lobby_model.text_channel and lobby_model.text_channel.id == interaction.channel.id:
            raise CustomError(
                "You can not use this command in the lobby's channel.")

        try:
            await db.delete_lobby(lobby_id)
        except Exception as e:
            self.bot.log_exception(f"Failed to remove lobby #{lobby_id}:", e)
            raise CustomError("Something went wrong! Please try again later.")

        for channel in [
            lobby_model.voice_channel,
            lobby_model.text_channel,
            lobby_model.category
        ]:
            if channel is not None:
                try:
                    await channel.delete()
                except HTTPException:
                    pass

        embed = Embed(description=f"Lobby #{lobby_model.id} has been removed.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name='empty-lobby',
        description='Empty the provided lobby and move users into Pre-Match channel.'
    )
    @app_commands.describe(lobby_id="Lobby ID.")
    @app_commands.checks.has_permissions(administrator=True)
    async def empty_lobby(self, interaction: Interaction, lobby_id: int):
        """"""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        lobby_model = await db.get_lobby_by_id(lobby_id, self.bot)
        guild_model = await db.get_guild_by_id(guild.id, self.bot)
        if not lobby_model:
            raise CustomError("Invalid Lobby ID")

        if lobby_model.guild.id != guild.id:
            raise CustomError("This lobby was not created in this server.")

        if self.awaiting[lobby_model.id]:
            raise CustomError(
                f"Unable to empty lobby #{lobby_model.id} at this moment, please try again later.")

        self.awaiting[lobby_model.id] = True
        for user in lobby_model.voice_channel.members:
            try:
                await user.move_to(guild_model.prematch_channel)
            except Exception as e:
                pass

        await db.clear_lobby_users(lobby_model.id)
        await self.update_queue_msg(lobby_model, title="Lobby has been emptied")
        self.awaiting[lobby_model.id] = False

        embed = Embed(description=f"Lobby #{lobby_model.id} has been emptied.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='edit-map-pool', description='Modify map pool')
    @app_commands.describe(lobby_id="Lobby ID.")
    @app_commands.checks.has_permissions(administrator=True)
    async def mpool(self, interaction: Interaction, lobby_id: int):
        """"""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        embed = Embed()

        lobby_model = await db.get_lobby_by_id(lobby_id, self.bot)
        if not lobby_model or lobby_model.guild.id != guild.id:
            raise CustomError("Invalid Lobby ID")

        guild_maps = await db.get_guild_maps(guild, lobby_model.game_mode)
        lobby_maps = await db.get_lobby_maps(lobby_id)
        placeholder = "Select maps from the list"
        options = [
            SelectOption(
                label=map_model.display_name,
                value=map_model.map_id,
                default=map_model in lobby_maps
            ) for map_model in guild_maps
        ]
        max_maps = len(guild_maps) if lobby_model.series == "bo1" else 7
        dropdown = DropDownView(user, placeholder, options, 7, max_maps)
        message = await interaction.followup.send(view=dropdown, wait=True)
        await dropdown.wait()

        if dropdown.selected_options is None:
            embed.description = "Timeout! Your haven't selected maps in time."
            await message.edit(embed=embed, view=None)
            return
        
        active_maps = list(filter(lambda x: str(x.map_id) in dropdown.selected_options, guild_maps))
        await db.update_lobby_maps(lobby_id, active_maps, lobby_maps)

        embed.description = f"Map pool for lobby **#{lobby_id}** updated successfully."
        embed.add_field(name="Active Maps", value='\n'.join(m.display_name for m in active_maps))
        await message.edit(embed=embed, view=None)

    @app_commands.command(name="add-map", description="Add a custom map")
    @app_commands.describe(
        display_name="Display map name. e.g. Dust II",
        dev_name="Map name in CS:GO. e.g. de_dust2",
    )
    @app_commands.choices(game_mode=GAME_MODE_CHOICES)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_custom_map(
        self,
        interaction: Interaction,
        display_name: str,
        dev_name: str,
        game_mode: app_commands.Choice[str]
    ):
        """"""
        await interaction.response.defer(ephemeral=True)
        embed = Embed()
        guild_maps = await db.get_guild_maps(interaction.guild, game_mode.value)
        count_maps = len(guild_maps)

        if count_maps == 23:
            raise CustomError("You have 23 maps, you cannot add more!")

        map_added = await db.create_custom_guild_map(
            interaction.guild, display_name, dev_name, game_mode.value
        )

        if map_added:
            embed.description = f"Map **{display_name}** added successfully `{count_maps + 1}/23`"
        else:
            embed.description = f"Map **{display_name}** already exists `{count_maps}/23`"

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='remove-map', description='Remove a custom map')
    @app_commands.describe(dev_name='Map name in CS:GO. e.g. de_dust2')
    @app_commands.choices(game_mode=GAME_MODE_CHOICES)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_custom_map(
        self,
        interaction: Interaction,
        dev_name: str,
        game_mode: app_commands.Choice[str]
    ):
        """"""
        await interaction.response.defer(ephemeral=True)
        guild_maps = await db.get_guild_maps(interaction.guild, game_mode.value)
        count_maps = len(guild_maps)
        guild_maps = list(filter(lambda x: x.dev_name == dev_name, guild_maps))

        if not guild_maps:
            raise CustomError("Map not exist!")

        await db.delete_guild_maps(interaction.guild, guild_maps, game_mode.value)

        description = f'Map removed successfully `{count_maps-1}/23`'
        embed = Embed(description=description)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="add-spectator", description="Add a user to the matches")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_spectator(self, interaction: Interaction, user: Member):
        """"""
        await interaction.response.defer()
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model:
            raise CustomError(f"User {user.mention} must be linked.")
        
        try:
            await db.insert_spectators(user, guild=interaction.guild)
        except UniqueViolationError:
            raise CustomError(f"User {user.mention} is already in spectators list")

        embed = Embed(description=f"User {user.mention} has successfully added to the spectators list")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="remove-spectator", description="Remove a user from the spectators list")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_spectator(self, interaction: Interaction, user: Member):
        """"""
        await interaction.response.defer()
        deleted = await db.delete_spectators(user, guild=interaction.guild)
        if not deleted:
            raise CustomError(f"User {user.mention} is not in spectators list")
        
        embed = Embed(description=f"User {user.mention} has successfully removed from spectators list")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="spectators-list", description="Show list of match spectators")
    async def spectators_list(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        spectators = await db.get_spectators(interaction.guild)
        
        if spectators:
            description = "\n".join(f"{idx}. {spec.user.mention}" for idx, spec in enumerate(spectators))
        else:
            description = "No spectators found"

        embed = Embed(description=description)
        await interaction.followup.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, user: Member, before: VoiceState, after: VoiceState):
        """"""
        if before.channel == after.channel:
            return

        async with self.lock:
            if before.channel is not None:
                lobby_model = await db.get_lobby_by_voice_channel(before.channel)
                if lobby_model and not self.awaiting[lobby_model.id]:
                    self.awaiting[lobby_model.id] = True
                    try:
                        await self._leave(user, lobby_model)
                    except Exception as e:
                        self.bot.log_exception(
                            "Uncaght exception when handling 'cogs.lobby._leave()' method:", e)
                    self.awaiting[lobby_model.id] = False

            if after.channel is not None:
                lobby_model = await db.get_lobby_by_voice_channel(after.channel)
                if lobby_model and lobby_model.text_channel and not self.awaiting[lobby_model.id]:
                    self.awaiting[lobby_model.id] = True
                    try:
                        await self._join(user, lobby_model)
                    except Exception as e:
                        self.bot.log_exception(
                            "Uncaught exception when handling 'cogs.lobby._join()' method:", e)
                    self.awaiting[lobby_model.id] = False

    async def _leave(self, user: Member, lobby_model: LobbyModel):
        """"""
        removed = await db.delete_lobby_users(lobby_model.id, [user])
        if removed:
            title = f"User {user.display_name} removed from the lobby"
            await self.update_queue_msg(lobby_model, title)

    async def _join(self, user: Member, lobby_model: LobbyModel):
        """"""
        queued_users = await db.get_lobby_users(lobby_model.id, lobby_model.guild)
        try:
            await self.add_user_to_lobby(user, lobby_model, queued_users)
        except JoinLobbyError as e:
            title = e.message
        else:
            title = f"User **{user.display_name}** added to the queue."
            queued_users += [user]

            if len(queued_users) == lobby_model.capacity:
                title = None
                guild_model = await db.get_guild_by_id(lobby_model.guild.id, self.bot)

                try:
                    queue_msg = await lobby_model.text_channel.fetch_message(lobby_model.message_id)
                except HTTPException as e:
                    embed = Embed(description="Lobby message")
                    queue_msg = await lobby_model.text_channel.send(embed=embed)

                unreadied_users = []
                if not lobby_model.auto_ready:
                    mentions_msg = await lobby_model.text_channel.send(''.join(u.mention for u in queued_users))
                    ready_view = ReadyView(queued_users, queue_msg)
                    await queue_msg.edit(embed=ready_view._embed_ready(), view=ready_view)
                    await ready_view.wait()
                    unreadied_users = set(queued_users) - ready_view.ready_users
                    try:
                        await mentions_msg.delete()
                    except Exception as e:
                        pass

                try:
                    await queue_msg.delete()
                except Exception as e:
                    pass

                if unreadied_users:
                    await db.delete_lobby_users(lobby_model.id, unreadied_users)
                    await self.move_to_channel(guild_model.prematch_channel, unreadied_users)
                else:
                    embed = Embed(description='Starting match setup...')
                    setup_match_msg = await lobby_model.text_channel.send(embed=embed)

                    map_pool = await db.get_lobby_maps(lobby_model.id)
                    match_cog = self.bot.get_cog('Match')
                    match_started = await match_cog.start_match(
                        lobby_model.guild,
                        setup_match_msg,
                        map_pool,
                        queue_users=queued_users,
                        game_mode=lobby_model.game_mode,
                        team_method=lobby_model.team_method,
                        captain_method=lobby_model.captain_method,
                        map_method=lobby_model.map_method,
                        series=lobby_model.series,
                        region=lobby_model.region,
                        season_id=lobby_model.season_id
                    )
                    if not match_started:
                        await self.move_to_channel(guild_model.prematch_channel, queued_users)

                    await db.clear_lobby_users(lobby_model.id)

        await self.update_queue_msg(lobby_model, title)

    async def add_user_to_lobby(self, user: Member, lobby_model: LobbyModel, queued_users: List[Member]):
        """"""
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        match_data = await db.get_user_match(user.id, lobby_model.guild)

        if not user_model or not user_model.steam:
            raise JoinLobbyError(user, "User not linked")
        if match_data:
            raise JoinLobbyError(user, "User in match")
        if user in queued_users:
            raise JoinLobbyError(user, "User in lobby")
        if len(queued_users) >= lobby_model.capacity:
            raise JoinLobbyError(user, "Lobby is full")
        try:
            await db.insert_lobby_user(lobby_model.id, user)
        except UniqueViolationError:
            raise JoinLobbyError(user, "Please try again")

    async def update_queue_msg(self, lobby_model: LobbyModel, title: str = None):
        """"""
        if not lobby_model.text_channel or not lobby_model.voice_channel:
            return

        queued_users = await db.get_lobby_users(lobby_model.id, lobby_model.guild)

        try:
            queue_message = await lobby_model.text_channel.fetch_message(lobby_model.message_id)
        except:
            queue_message = await lobby_model.text_channel.send(embed=Embed(description="New Queue Message"))
            await db.update_lobby_data(lobby_model.id, {'last_message': queue_message.id})

        embed = self._embed_queue(
            title, lobby_model, queued_users)
        await queue_message.edit(embed=embed, view=None)

    def _embed_queue(self, title: str, lobby_model: LobbyModel, queued_users: List[Member]):
        """"""
        embed = Embed(title=title)

        info_str = f"Game mode: *{lobby_model.game_mode.capitalize()}*\n" \
                   f"Teams method: *{lobby_model.team_method.capitalize()}*\n" \
                   f"Captains method: *{lobby_model.captain_method.capitalize()}*\n" \
                   f"Maps method: *{lobby_model.map_method.capitalize()}*\n" \
                   f"Series: *{lobby_model.series.capitalize()}*\n" \
                   f"Auto-ready: *{'ON' if lobby_model.auto_ready else 'OFF'}*"

        queued_players_str = "*Lobby is empty*" if not queued_users else ""
        for num, user in enumerate(queued_users, start=1):
            queued_players_str += f'{num}. {user.mention}\n'

        embed.add_field(name="**__Settings__**", value=info_str, inline=False)
        embed.add_field(
            name=f"**__Players__** `({len(queued_users)}/{lobby_model.capacity})`:",
            value=queued_players_str
        )
        embed.set_author(name=f"Lobby #{lobby_model.id}")
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        return embed

    async def move_to_channel(self, channel: VoiceChannel, users: List[Member]):
        """"""
        for user in users:
            try:
                await user.move_to(channel)
            except HTTPException as e:
                self.bot.logger.warning(
                    f"Unable to move user \"{user.display_name}\" to voice channel \"{channel.name}\": {e.text}")


async def setup(bot: G5Bot):
    await bot.add_cog(LobbyCog(bot))
