# -*- coding: utf-8 -*-
import asyncio
import copy
from datetime import datetime, date
from enum import Enum
import logging
import math
import nextcord
import random
import time
import threading
from nextcord.emoji import Emoji
from nextcord.enums import ButtonStyle
from nextcord.ext import commands, menus
from nextcord.interactions import Interaction
from nextcord.partial_emoji import PartialEmoji
import re
from tabulate import tabulate
tabulate.PRESERVE_WHITESPACE = True

import validators

from db.zBot_db_orm import *
from ui.menus_string_data import *
from ui.ui_util import *

########################################################################################################################
# Menu POD Classes
########################################################################################################################
class MenuItem():
    def __init__(self, label:nextcord.Emoji, func, custom_id, short_description, help_text, include_interaction=True) -> None:
        self.label = label
        self.custom_id = custom_id
        self.short_description = short_description
        self.help_text = help_text
        if include_interaction:
            self.func = func
        else:
            self.func = self.remove_interaction
            self.caller_func = func

    async def remove_interaction(self, interaction, payload):
        return await self.caller_func(payload)
    
class EmbedField():
    def __init__(self, name, value, inline=False) -> None:
        self.name = name
        self.value = value
        self.inline = inline

class ToggleField():
    def __init__(self, 
                 payload,
                 toggle_func,
                 embed_field: EmbedField,
                 button_style: nextcord.ButtonStyle,
                 custom_id: str,
                 emoji: nextcord.Emoji | nextcord.PartialEmoji) -> None:
        self.toggle_func = toggle_func
        self.payload = payload
        self.embed_field = embed_field
        self.button_style = button_style
        self.custom_id = custom_id
        self.emoji = emoji

########################################################################################################################
class zButton(nextcord.ui.Button):
    def __init__(self,
                 menu_item: MenuItem,
                 payload = None,
                 *,
                 label : str = None,
                 style: ButtonStyle = ButtonStyle.primary,
                 disabled: bool = False,
                 url: str | None = None,
                 emoji: str | Emoji | PartialEmoji | None = None,
                 row: int | None = None) -> None:
        self.menu_item = menu_item
        self.payload = payload
        super().__init__(style=style,
                         label=label,
                         disabled=disabled,
                         custom_id=menu_item.custom_id,
                         url=url,
                         emoji=None if menu_item.label is None else PartialEmoji.from_str(menu_item.label),
                         row=row)

    async def callback(self, interaction: Interaction) -> None:
        return await self.menu_item.func(interaction, self.payload)
    
class zToggleButton(nextcord.ui.Button):
    def __init__(self,
                 payload,
                 toggle_field: ToggleField,
                 *,
                 label : str = None,
                 style: ButtonStyle = ButtonStyle.primary,
                 disabled: bool = False,
                 url: str | None = None,
                 emoji: str | Emoji | PartialEmoji | None = None,
                 row: int | None = None) -> None:
        self.toggle_field = toggle_field
        self.payload = payload
        super().__init__(style=style,
                         label=label,
                         disabled=disabled,
                         custom_id=toggle_field.custom_id,
                         url=url,
                         emoji=emoji,
                         row=row)

    async def callback(self, interaction: Interaction) -> None:
        return await self.toggle_field.toggle_func(interaction, self.payload)

########################################################################################################################
class zButtonMenu(menus.ButtonMenu):
    def __init__(self, 
                 payload: any,
                 menu_item_list: list[MenuItem],
                 *,
                 use_channel: bool = False,
                 title: str = "",
                 description: str = "",
                 footer: str = DefaultFooter,
                 color: int = 0x5865F2,
                 embed=None) -> None:

        self.menu_item_list = menu_item_list
        self.use_channel = use_channel
        self.title = title
        self.description = description
        self.footer = footer
        self.color = color
        self.embed = embed

        super().__init__(timeout=None)

        for i in menu_item_list:
            if type(payload) is list:
                button = zButton(i, payload[menu_item_list.index(i)])
            else:
                button = zButton(i, payload)
            self.add_item(button)
    
    async def send_initial_message(self, ctx, channel):
        if self.embed is None:
            # Send embed message with `self` as the view
            self.embed = nextcord.Embed(title=self.title, description=self.description, color=self.color)
            if self.footer is not None:
                self.embed.set_footer(text=self.footer)

            for i in self.menu_item_list:
                self.embed.add_field(name=f"{i.label} - {i.short_description}", value=i.help_text, inline=False)
        
        if self.use_channel:
            return await channel.send("", view=self, embed=self.embed)
        else:
            await send_message(self.interaction, "", view=self, embed=self.embed)
            return await self.interaction.original_message()

    async def send_updated_message(self, embed):
        # Send the updated message
        self.embed = embed
        await self.message.edit(embed=self.embed, view=self)

########################################################################################################################
class zConfirmMenu(menus.ButtonMenu):
    def __init__(self, msg: str):
        super().__init__(timeout=None, clear_buttons_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        await send_message(self.interaction, self.msg, view=self)
        return await self.interaction.original_message()

    @nextcord.ui.button(emoji=PartialEmoji.from_str('✅'))
    async def on_confirm(self, button, interaction):
        self.result = True
        self.stop()

    @nextcord.ui.button(emoji=PartialEmoji.from_str('❌'))
    async def on_cancel(self, button, interaction):
        self.result = False
        self.stop()

    async def prompt(self, interaction: nextcord.Interaction):
        await menus.Menu.start(self, interaction=interaction, wait=True)
        return self.result
    
########################################################################################################################
class zToggleButtonMenu(menus.ButtonMenu):
    def __init__(self, 
                 toggle_fields: list[ToggleField],
                 *,
                 use_channel: bool = False,
                 title: str = "",
                 description: str = "",
                 footer: str = None,
                 color: int = 0x5865F2,
                 embed=None) -> None:

        self.toggle_fields = toggle_fields
        self.use_channel = use_channel
        self.title = title
        self.description = description
        self.footer = footer
        self.color = color
        self.embed = embed

        super().__init__(timeout=None)

        for i in self.toggle_fields:
            self.add_item(zToggleButton(payload=(self, i), toggle_field=i, style=i.button_style, emoji=i.emoji))
    
    async def send_initial_message(self, ctx, channel):
        if self.embed is None:
            # Send embed message with `self` as the view
            self.embed = nextcord.Embed(title=self.title, description=self.description, color=self.color)
            if self.footer is not None:
                self.embed.set_footer(text=self.footer)

            for i in self.toggle_fields:
                self.embed.add_field(name=i.embed_field.name, value=i.embed_field.value, inline=i.embed_field.inline)
        
        if self.use_channel:
            return await channel.send("", view=self, embed=self.embed)
        else:
            await send_message(self.interaction, "", view=self, embed=self.embed)
            return await self.interaction.original_message()

    async def send_updated_message(self, embed):
        # Send the updated message
        self.embed = embed
        await self.message.edit(embed=self.embed, view=self)
    
########################################################################################################################
class zRaceListPageSource(menus.ListPageSource):
    def __init__(self,
                 races_list,
                 server_id,
                 per_page: int=4,
                 use_inline_fields=False,
                 static_embed_fields=[],
                 title=None,
                 body_text=None,
                 user_id=None) -> None:
        self.server_id = server_id
        self.use_inline_fields = use_inline_fields
        self.static_embed_fields = [] if static_embed_fields is None else static_embed_fields
        self.title = title
        self.body_text = body_text
        self.user_id = user_id
        self.race_emojis = get_emoji_list()

        super().__init__(entries=races_list, per_page=per_page)

    def format_page(self, menu, races):
        random.shuffle(self.race_emojis)
        menu.update_buttons(races, self.race_emojis)

        embed = nextcord.Embed(color=nextcord.Colour.random(), title=self.title, description=self.body_text)
        
        for f in self.static_embed_fields:
            embed.add_field(name=f.name, value=f.value, inline=f.inline)
        
        for i, r in enumerate(races):
            embed.add_field(name=f"{self.race_emojis[i]} {r.id}",
                            value=get_race_embed_field_value(r, self.user_id),
                            inline=self.use_inline_fields)
        return embed

class zRaceListMenuPages(menus.ButtonMenuPages, inherit_buttons=False):
    def __init__(self, source: zRaceListPageSource, *, style=ButtonStyle.secondary, timeout=None) -> None:
        super().__init__(source, style=style, timeout=timeout)
        
        # Disable buttons that are unavailable
        self._disable_unavailable_buttons()

        self.disabled_buttons = []
        self.race_buttons = []
        for i in range(0, source.per_page):
            button = zButton(MenuItem(None, show_race_details, f"race_button_{i}", "Race Info", "View race info for labelled race ID"), 0, label="[RaceID]")
            self.race_buttons.append(button)
            self.add_item(button)
            self.disabled_buttons.append(None)

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(zButton(MenuItem(FirstPageEmoji, self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(PreviousPageEmoji, self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(NextPageEmoji, self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(LastPageEmoji, self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    def update_buttons(self, races, emojis=None):
        # Update the button list based on how many races we need to display
        for i in range(0, self.source.per_page):
            if i >= len(races):
                self.disabled_buttons[i] = self.race_buttons[i]
                self.race_buttons[i] = None
                self.remove_item(self.disabled_buttons[i])
            elif self.race_buttons[i] is None:
                self.race_buttons[i] = self.disabled_buttons[i]
                self.disabled_buttons[i] = None
                self.add_item(self.race_buttons[i])
        
        # Update the race buttons
        for i,r in enumerate(races):
            self.race_buttons[i].label = emojis[i] if emojis is not None else f"{r.id}"
            self.race_buttons[i].payload = r.id
            self.race_buttons[i].disabled = False

    async def send_initial_message(self, ctx, channel):
        races = await self.source.get_page(0)
        
        await send_message(self.interaction, None, view=self, embed=self.source.format_page(self, races))
        return await self.interaction.original_message()
    
########################################################################################################################
class zCategoryListPageSource(menus.ListPageSource):
    def __init__(self, category_list, server_id, per_page: int=10) -> None:
        self.server_id = server_id
        super().__init__(entries=category_list, per_page=per_page)
        self.category_emojis = get_emoji_list()
    
    def format_page(self, menu, categories):
        random.shuffle(self.category_emojis)
        menu.update_buttons(categories, self.category_emojis)

        embed = nextcord.Embed(color=nextcord.Colour.random(), title="Category List", description=f"Active Categories")
        for i, c in enumerate(categories):
            embed.add_field(name=f"{self.category_emojis[i]} - {c.name}", value=c.description, inline=False)
        return embed

class zCategoryListMenuPages(menus.ButtonMenuPages, inherit_buttons=False):
    def __init__(self, source: zCategoryListPageSource, *, style=ButtonStyle.secondary, timeout=None) -> None:
        super().__init__(source, style=style, timeout=timeout)
        # Disable buttons that are unavailable
        self._disable_unavailable_buttons()
        
        self.disabled_buttons = []
        self.category_buttons = []
        for i in range(0, source.per_page):
            button = zButton(MenuItem(None, show_category_info, f"category_button_{i}", "Category Leaderboard", "View leaderboard for category"), 0, label="[CategoryID]")
            self.category_buttons.append(button)
            self.add_item(button)
            self.disabled_buttons.append(None)

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(zButton(MenuItem(FirstPageEmoji, self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(PreviousPageEmoji, self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(NextPageEmoji, self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(LastPageEmoji, self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    def update_buttons(self, categories, emojis=None):
        # Update the button list based on how many categories we need to display
        for i in range(0, self.source.per_page):
            if i >= len(categories):
                self.disabled_buttons[i] = self.category_buttons[i]
                self.category_buttons[i] = None
                self.remove_item(self.disabled_buttons[i])
            elif self.category_buttons[i] is None:
                self.category_buttons[i] = self.disabled_buttons[i]
                self.disabled_buttons[i] = None
                self.add_item(self.category_buttons[i])

        # Update the category leaderboard buttons
        for i,c in enumerate(categories):
            self.category_buttons[i].label = emojis[i] if emojis is not None else f"{c.id}"
            self.category_buttons[i].payload = c.id
            self.category_buttons[i].disabled = False

    async def send_initial_message(self, ctx, channel):
        categories = await self.source.get_page(0)
        
        await send_message(self.interaction, embed=self.source.format_page(self, categories), view=self)
        return await self.interaction.original_message()
    
########################################################################################################################
class zRaceLeaderboardPageSource(menus.ListPageSource):
    def __init__(self, submission_list, server_id, bot_client, *, per_page: int=10, title=None, body_text=None) -> None:
        self.server_id = server_id
        self.bot_client = bot_client
        self.title = title
        self.body_text = body_text

        super().__init__(entries=submission_list, per_page=per_page)

    async def format_page(self, menu, submissions):
        return await get_race_leaderboard_embed(self.title, self.body_text, submissions, menu.current_page, self.per_page, self.bot_client)

class zRaceLeaderboardMenuPages(menus.ButtonMenuPages, inherit_buttons=False):
    def __init__(self, source: zRaceLeaderboardPageSource, *, style=ButtonStyle.secondary, timeout=None) -> None:
        super().__init__(source, style=style, timeout=timeout)
        
        # Disable buttons that are unavailable
        self._disable_unavailable_buttons()

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(zButton(MenuItem(FirstPageEmoji, self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(PreviousPageEmoji, self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(NextPageEmoji, self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(LastPageEmoji, self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    async def send_initial_message(self, ctx, channel):
        submissions = await self.source.get_page(0)
        
        embed = await self.source.format_page(self, submissions)
        await send_message(self.interaction, None, view=self, embed=embed)
        return await self.interaction.original_message()

########################################################################################################################
class zCategoryPointsLeaderboardPageSource(menus.ListPageSource):
    def __init__(self, points_list, bot_client, per_page: int=10, title=None, body_text=None) -> None:
        self.title = title
        self.body_text = body_text
        super().__init__(entries=points_list, per_page=per_page)
    
    async def format_page(self, menu, points_list):
        return await get_category_leaderboard_embed(self.title,
                                                    self.body_text,
                                                    points_list,
                                                    menu.current_page,
                                                    self.per_page,
                                                    self.bot_client)

########################################################################################################################
# View which contains race info buttons
class zRaceInfoButtonView(nextcord.ui.View):
    def __init__(self, race_id):
        super().__init__(timeout=None)
        self.race_id = race_id

    async def check_can_submit(self, interaction):
        race = get_race(self.race_id)
        if race is not None:
            if race.state == RaceState.Inactive:
                await send_message(interaction, "Cannot create a submission, this race is Inactive")
                return False
            if race.state == RaceState.Completed and not race.category_id.allow_completed_submit:
                await send_message(interaction, "The category for this race does not permit submitting to a completed race.")
                return False
        return True
    
    @nextcord.ui.button(style=nextcord.ButtonStyle.grey, emoji=PartialEmoji.from_str(TimeEmoji))
    async def submit_time_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await self.check_can_submit(interaction):
            # Lookup if the user has a submission for this race already
            submission = get_race_submission(interaction.user.id, self.race_id)
            submit_handler = zRaceSubmitHandler(self.race_id, submission)
            await submit_handler.send_submit_modal(interaction)

    @nextcord.ui.button(style=nextcord.ButtonStyle.grey, emoji=PartialEmoji.from_str(ForfeitEmoji))
    async def forfeit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await self.check_can_submit(interaction):
            # Check if the user has already submitted a time for this race
            if get_race_submission(interaction.user.id, self.race_id) is not None:
                await send_message(interaction, "Time already submitted for this race, use `Submit/Edit` button to edit")
                return
            else:
                forfeit_race(interaction.user.id, self.race_id)
                race = get_race(self.race_id)
                await do_post_submit_actions(interaction, race, interaction.user.id)
                await send_message(interaction, "Forfeit submitted")

    @nextcord.ui.button(style=nextcord.ButtonStyle.grey, emoji=PartialEmoji.from_str(LeaderboardEmoji))
    async def leaderboard_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if can_view_race_leaderboard(self.race_id, interaction.user.id):
            await show_race_leaderboard(interaction, self.race_id)
        else:
            await send_message(interaction, "You must submit a time, forfeit or wait for the race to be completd to view the leaderboard")

    def add_static_embed_fields(embed: nextcord.Embed):
        embed.add_field(name=f"{TimeEmoji} - Submit/Edit Time", value="Submit a time for this race or edit an already submitted time.", inline=False)
        embed.add_field(name=f"{ForfeitEmoji} - Forfeit", value="Forfeit from this race. Will submit a max time on your behalf and unlock the leaderboard.", inline=False)
        embed.add_field(name=f"{LeaderboardEmoji} - View Leaderboard", value="View the leaderboard for this race.", inline=False)

########################################################################################################################
# View which contains category info and buttons
class zCategoryInfoButtonView(nextcord.ui.View):
    def __init__(self, category_id):
        super().__init__(timeout=None)
        self.category_id = category_id

    @nextcord.ui.button(style=nextcord.ButtonStyle.grey, emoji=PartialEmoji.from_str(CompletedRacesEmoji))
    async def completed_races_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Get list of completed category races
        races = get_completed_races_by_category(self.category_id)

        # Then show it as a menu
        race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id, use_inline_fields=True),
                                            style=ButtonStyle.secondary,
                                            timeout=None)
    
        await race_list_menu.start(interaction=interaction, ephemeral=True)

    @nextcord.ui.button(style=nextcord.ButtonStyle.grey, emoji=PartialEmoji.from_str(LeaderboardEmoji))
    async def leaderboard_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await show_category_leaderboard(interaction, self.category_id)

    def add_static_embed_fields(embed: nextcord.Embed):
        embed.add_field(name=f"{CompletedRacesEmoji} - Completed Races", value="View completed races in this category", inline=False)
        embed.add_field(name=f"{LeaderboardEmoji} - View Leaderboard", value="View the most recent leaderboard for this category", inline=False)

#####################################################################################################################
# Handles a user race submission action
class zRaceSubmitHandler():
    def __init__(self, race_id, submission=None, include_points=False, user_id=None):
        self.race = get_race(race_id)
        self.submission = submission
        self.include_points = include_points
        self.user_id = user_id

        # Set the title
        if submission is None:
            title = "Submit Time"
        else:
            title = f"Edit Submission"

        self.finish_time_id = "finish_time"
        self.comment_id     = "comment"

        # Create the modal fields
        self.fields = [
            zField(custom_id=self.finish_time_id,
                   label="Enter finish time in format `H:MM:SS`",
                   default_value=submission.finish_time if submission is not None else None,
                   required=True),
            zField(custom_id=self.comment_id,
                   label="Comment",
                   default_value=submission.comment if submission is not None else None,
                   required=False),
        ]

        # Include a points field if it was requested and this category supports scoring
        self.points_id = "points"
        if include_points and self.race.category_id.points_type != PointsType.NoScoring and self.race.state == RaceState.Completed:
            self.fields.append(zField(custom_id=self.points_id,
                                      label="Points",
                                      default_value=submission.points if submission is not None else None,
                                      placeholder="Category points for this submission",
                                      required=False))

        # Add any extra info fields
        for a in self.race.extra_info_assignments:
            t = get_extra_info_type(a.info_type_id)
            info = None if self.submission is None else get_extra_info(self.submission.id, a.info_type_id)
            self.fields.append(zField(
                custom_id=str(a.info_type_id),
                label=t.name,
                default_value=info.data if info is not None else None,
                placeholder=t.description,
                required=a.required))

    ####################################################################################################################
    # Displays the multi-page modal used to capture submission info
    async def send_submit_modal(self, interaction):
        modal_sender = zMultiPageModalSender()
        await modal_sender.send_modal(interaction,
                                      self.fields,
                                      self.on_submit,
                                      "Race Submission")

    ####################################################################################################################
    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, interaction, submitted_values):
        # If we don't already have a DB entry create one now
        if self.submission is None:
            self.submission = AsyncRaceSubmission()
            self.submission.race_id = self.race.id
            self.submission.user_id = self.user_id if self.user_id is not None else interaction.user.id
            self.submission.submit_datetime = zBot_now()

        for i, v in enumerate(submitted_values):
            match self.fields[i].custom_id:
                case self.finish_time_id:
                    if game_time_is_valid(v) is False:
                        await send_message(interaction, "**ERROR** Finish time must be in format `H:MM:SS`")
                        return
                    else:
                        self.submission.finish_time = v
                    self.submission.save()
                case self.comment_id:
                    if v is not None and v != "":
                        self.submission.comment = v
                case self.points_id:
                    if v is not None and v != "":
                        try:
                            self.submission.points = int(v)
                        except:
                            await send_message(interaction, "**ERROR** Points must be an integer")
                            return
                case _:
                    success = await self.save_extra_info(interaction, self.fields[i], v)
                    if not success:
                        return
        
        self.submission.save()
        await send_message(interaction, "Race Submission Saved")

        await do_post_submit_actions(interaction, self.race, self.submission.user_id)

    ####################################################################################################################
    # Saves an individual extra info value
    async def save_extra_info(self, interaction, field: zField, value) -> bool:
        data_is_valid = True
        if value is None or value == "":
            # The modal handles required fields so if we have an empty value it's because it's optional,
            # so just return without creating a DB entry
            return data_is_valid
        
        # We store the info_type_id in the custom ID of the zField
        info = get_extra_info(self.submission.id, field.custom_id)

        # We need to create a new DB entry
        if info is None:
            info = AsyncRaceExtraInfo()
            info.submission_id = self.submission.id
            info.info_type_id = int(field.custom_id)

        # Validate the data
        info_type = get_extra_info_type(info.info_type_id)
        
        # Validate the value based on the type
        match(info_type.var_type):
            case VarType.Str:
                # No validation required
                info.data = value
            case VarType.Int:
                try:
                    info.data = int(value)
                except:
                    await send_message(interaction, f"**ERROR** {info_type.name} must be an integer")
                    data_is_valid = False
            case VarType.Float:
                try:
                    info.data = float(value)
                except:
                    await send_message(interaction, f"**ERROR** {info_type.name} must be a valid floating point number")
                    data_is_valid =  False
            case VarType.GameTime:
                if game_time_is_valid(value) is False:
                    await send_message(interaction, f"**ERROR** {info_type.name} must be in format `H:MM:SS`")
                    data_is_valid = False
                else:
                    info.data = value
            case VarType.DateTime:
                if datetime_is_valid(value) is False:
                    await send_message(interaction, f"**ERROR** {info_type.name} must be in one of the following formats: `YYYY-MM-DD`, `H:MM:SS` or `YYYY-MM-DD H:MM:SS`")
                    data_is_valid = False
            case _:
                logging.info(f"Unknown VarType found in `save_extra_info`: {info_type.var_type} for extra info type ID {info_type.id}")
                info.data = value

        if data_is_valid:
            info.save()

        return data_is_valid
    
########################################################################################################################
class zRaceAddEditModal(zModal):
    def __init__(self, server_id, category_id, race=None):
        self.server_id = server_id
        self.race = race
        if race is None:
            self.category_id = category_id
        else:
            self.category_id = race.category_id

        # Save the race for later reference in the submit handler
        self.race = race

        # Set the title
        if race is None:
            title = "Add Race"
        else:
            title = f"Edit Race ID {race.id}"

        self.seed_id                = "seed"
        self.hash_id                = "hash"
        self.description_id         = "description"
        self.extra_info_id          = "extra_info"

        # Create the modal fields
        fields = {
            self.seed_id: nextcord.ui.TextInput(
                label="Seed",
                required=True,
                custom_id=self.seed_id,
                row=1,
                default_value=race.seed if race is not None else None),
            self.description_id: nextcord.ui.TextInput(
                label="Description",
                required=True,
                custom_id=self.description_id,
                row=2,
                default_value=race.description if race is not None else None),
            self.hash_id: nextcord.ui.TextInput(
                label="Hash",
                required=False,
                custom_id=self.hash_id,
                row=3,
                default_value=race.hash if race is not None else None),
            self.extra_info_id: nextcord.ui.TextInput(
                label="Additional Instructions",
                required=False,
                custom_id=self.extra_info_id,
                row=4,
                default_value=race.additional_instructions if race is not None else None),
        }
        # Call the base class init
        super().__init__(fields, self.on_submit, title)

    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, interaction, modal):
        # If we don't already have a DB entry create one now
        race_is_new = False
        if self.race is None:
            self.race = AsyncRace()
            self.race.server_id = self.server_id
            self.race.category_id = self.category_id
            self.race.create_datetime = date.today().isoformat()
            race_is_new = True

        for c in modal.children:
            match c.custom_id:
                case self.seed_id:
                    self.race.seed = c.value
                case self.hash_id:
                    if c.value is not None:
                        self.race.hash = c.value
                case self.description_id:
                    self.race.description = c.value
                case self.extra_info_id:
                    if c.value is not None:
                        self.race.additional_instructions = c.value
                case _:
                    continue
        self.race.save()

        if race_is_new:
            # Create default extra info assignments based on category
            cat_infos = AsyncRaceExtraInfoAssignment.select().where(
                AsyncRaceExtraInfoAssignment.category_id == self.category_id)
            for c in cat_infos:
                a = AsyncRaceExtraInfoAssignment()
                a.info_type_id = c.info_type_id
                a.race_id = self.race.id
                a.required = c.required
                a.save()
            
            # Activate the race if the category toggle indicates we should
            if self.race.category_id.activate_new_races:
                # Get the previous race in this category to mark it as completed
                recent_race = get_most_recent_race(self.race.category_id.id)
                if recent_race is not None and recent_race.state == RaceState.Active:
                    recent_race.state = RaceState.Completed
                    recent_race.save()
                    score_race(recent_race)
                    update_race_leaderboard(interaction, recent_race)

                self.race.state = RaceState.Active
                self.race.save()
                await handle_activate_race(interaction, self.race)

        await send_message(interaction, "Race Info Saved")
        self.stop()

########################################################################################################################
class zCategoryAddEditModal(zModal):
    def __init__(self, category=None):
        # Save the category for later reference in the submit handler
        self.category = category

        # Set the title
        if category is None:
            title = "Add Category"
        else:
            title = f"Edit Category ID {category.id}"

        self.name_id = "name"
        self.desc_id = "desc"
        # Create the modal fields
        fields = {
            self.name_id: nextcord.ui.TextInput(label="Category Name",
                                 required=True,
                                 row=1,
                                 custom_id=self.name_id,
                                 default_value=category.name if category is not None else None),
            self.desc_id: nextcord.ui.TextInput(label="Category Description",
                                 required=False,
                                 custom_id=self.desc_id,
                                 row=2,
                                 default_value=category.description if category is not None else None),
        }
        # Call the base class init
        super().__init__(fields, self.on_submit, title)

    ####################################################################################################################
    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, interaction, modal):
        if self.category is None:
            # Create a new category
            self.category = AsyncRaceCategory()
            self.category.server_id = interaction.guild_id
            self.category.active = True

        for c in modal.children:
            match c.custom_id:
                case self.name_id:
                    self.category.name = c.value
                case self.desc_id:
                    self.category.description = c.value
                case _:
                    continue
        try:
            self.category.save()
            await send_message(interaction, f"Saved category {self.category.name}")
            self.stop()
        except:
            await send_message(interaction, f"FAILED to save category {self.category.name}")

########################################################################################################################
class zExtraInfoTypeAddEditModal(zModal):
    def __init__(self, extra_info_type_id=None):
        # Lookup the category if an ID was provided
        info_type = get_extra_info_type(extra_info_type_id)

        # Save the category for later reference in the submit handler
        self.info_type = info_type

        # Set the title
        if info_type is None:
            title = "Add Extra Info Type"
        else:
            title = f"Edit Extra Info ID {info_type.id}"

        self.name_id = "name"
        self.desc_id = "desc"
        # Create the modal fields
        fields = {
            self.name_id: nextcord.ui.TextInput(label="Type Name",
                                 required=True,
                                 row=1,
                                 custom_id=self.name_id,
                                 default_value=info_type.name if info_type is not None else None),
            self.desc_id: nextcord.ui.TextInput(label="Type Description",
                                 required=False,
                                 custom_id=self.desc_id,
                                 row=2,
                                 default_value=info_type.description if info_type is not None else None),
        }
        # Call the base class init
        super().__init__(fields, self.on_submit, title)

    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, interaction, modal):
        if self.info_type is None:
            # Create a new type
            self.info_type = AsyncRaceExtraInfoType()
            self.info_type.server_id = interaction.guild_id

        for c in modal.children:
            match c.custom_id:
                case self.name_id:
                    self.info_type.name = c.value
                case self.desc_id:
                    self.info_type.description = c.value
                case _:
                    continue

        # Send a Select with options for the variable type
        vartype_select_view = zSingleSelectView(VarType.SelectOptionList.copy(), self.on_vartype_select, "Choose Data Type...")
        await send_message(interaction, view=vartype_select_view)

    async def on_vartype_select(self, vartype, interaction):
        self.info_type.var_type = vartype
        try:
            self.info_type.save()
            await send_message(interaction, f"Saved info type {self.info_type.name}")
        except:
            await send_message(interaction, f"FAILED to save info type {self.info_type.name}")

########################################################################################################################
# Category Menu Functions
########################################################################################################################
async def create_edit_category_command(interaction, payload):
    await defer(interaction)
    
    if not user_is_mod(interaction.guild, interaction.user):
        await send_message(interaction, "You must be a race moderator to use this command.")
        return

    # Get a list of categories
    select_list = get_category_select_list(interaction.guild_id)
    
    # Add the option for creating a new category to the front of the list
    select_list.insert(0, nextcord.SelectOption(label="Create New...", value=0, description="Create a new category."))
    
    # Prompt the user to select an option
    view = zSingleSelectView(select_list, create_edit_category, "Choose Category..")
    await send_message(interaction, view=view)

async def create_edit_category(category_id, interaction):
    if category_id == 0:
        # Create a new category
        modal = zCategoryAddEditModal(None)
        await interaction.response.send_modal(modal)
        # Once the modal is done, get the category to send the category edit menu
        await modal.wait()
        category_id = modal.category.id
    
    # Send the category edit menu
    if category_id is not None:
        await send_category_menu(interaction, category_id)

########################################################################################################################
async def category_edit_description(interaction, category):
    await interaction.response.send_modal(zCategoryAddEditModal(category))

########################################################################################################################
async def category_delete(interaction, category):
    # Check if there are any races created for this category
    races = get_category_races(category.id)
    
    if len(races) > 0:
        # If there are races in created in this category, warn the user that the category cannot be deleted
        await send_message(interaction, f"Category {category.name} cannot be deleted because there are races created for it.")
    else:
        # Otherwise we can delete the category, start with any extra info assignments
        extra_info_assignments = get_category_extra_info_assignments(category.id)
        for a in extra_info_assignments:
            a.delete_instance()

        # Then delete the actual category
        name = category.name
        category.delete_instance()
        await send_message(interaction, f"Category {category.name} has been deleted.")

########################################################################################################################
async def category_edit_scoring(interaction, category):
    await defer(interaction)

    # If there are completed races in this category, don't allow the scoring type to change
    races = get_completed_races_by_category(category.id)
    if races is not None and len(races) > 0:
        await send_message(interaction, "Cannot change scoring method for a category that has completed races.")
        return

    select_list = copy.deepcopy(PointsType.SelectOptionList)
    if category.points_type is None:
        select_list[0].default = True
    for s in select_list:
        
        if s.value == category.points_type:
            s.default = True
            break
    
    selected = await zSingleSelectView(select_list, None, "Choose Scoring Method...").prompt(interaction)
    
    curr_type = category.points_type
    # If the current points type is Trueskill and the user is changing it, remove any existing params
    if curr_type == PointsType.Trueskill and selected != PointsType.Trueskill:
        curr_params = get_category_trueskill_params(category.id)
        if curr_params is not None:
            curr_params.delete_instance()
    
    category.points_type = selected if selected != 0 else None
    category.save()

    # If the new points type is Trueskill and the old one was not, create trueskill params
    if selected == PointsType.Trueskill and curr_type != PointsType.Trueskill:
        create_default_trueskill_params(category.id)

    await send_message(interaction, f"Category Scoring Method Saved")

########################################################################################################################
async def category_edit_submit_role(interaction, category):
    await defer(interaction)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)

    logging.info(f"{get_user_name_str(interaction.user.id, interaction.user)} selected submit role: {selected_role} for category {category.id}")
    category.submit_role = selected_role
    category.save()
    await send_message(interaction, "Category Submit Role Saved")

########################################################################################################################
async def category_edit_create_role(interaction, category):
    await defer(interaction)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)
    logging.info(f"{get_user_name_str(interaction.user.id, interaction.user)} selected create role: {selected_role} for category {category.id}")
    category.create_role = selected_role
    category.save()
    await send_message(interaction, "Category Create Role Saved")

########################################################################################################################
async def category_edit_leaderboard_channel(interaction, category):
    await defer(interaction)

    logging.info(f"category_edit_leaderboard_channel")

    # Prompt for the new desired channel
    selected_channel = await prompt_for_channel(interaction)

    if selected_channel is None:
        return

    logging.info(f"{get_user_name_str(interaction.user.id, interaction.user)} selected leaderboard channel: {selected_channel.name} for category {category.id}")
    
    # Post an updated leaderboard in the new leaderboard channel
    await post_channel_category_leaderboard(interaction, selected_channel, category.id, interaction.client)
    await send_message(interaction, "Category Leaderboard Updated")
    

########################################################################################################################
async def category_edit_points(interaction, category):
    await defer(interaction)

    # Find racers who have submissions for this category
    points_list = get_category_points(category.id)
    server = get_server_from_interaction(interaction)
    
    # Prompt with a list of racers and their current points
    select_list = [nextcord.SelectOption(label=f"Cancel...", value=0, description="Cancel the operation")]
    for p in points_list:
        member = await server.fetch_member(p.user_id)
        member_name = get_user_name_str(p.user_id, member)
        select_list.append(nextcord.SelectOption(label=f"{member_name} - {p.points}", value=p.id, description=f"{member_name} Current Points: {p.points}"))

    view = zSingleSelectView(select_list, category_edit_db_points, "Choose Racer To Modify...")
    await send_message(interaction, view=view)

async def category_edit_db_points(points_id, interaction):
    db_points = get_category_points_by_id(points_id)
    server = get_server_from_interaction(interaction)
    if db_points is not None:
        # Ask what the new points value should be
        member = await server.fetch_member(db_points.user_id)
        member_name = get_user_name_str(db_points.user_id, member)
        new_points = await prompt_for_value(interaction,
                                            f"Enter New Points for `{member_name}`",
                                            "Points",
                                            str(db_points.points))
        # Update the points value
        logging.info(f"{get_user_name_str(interaction.user.id, interaction.user)} changed points for {member_name} from {db_points.points} to {new_points}")
        db_points.points = int(new_points)
        db_points.save()
        await send_message(interaction, f"Points for {member_name} updated to {new_points}")

        # TODO Update the leaderboard if there is a leaderboard channel
    else:
        await send_message(interaction, "Cancelled")

########################################################################################################################
async def category_assign_extra_info(interaction, category):
    # Get a list of extra info types
    select_list = get_extra_info_type_select_list(interaction.guild_id)

    # Update the labels for the items that are already assigned
    for s in select_list:
        if check_category_assignment_exists(s.value, category.id):
            s.label = f"✅ {s.label}"

    # Prompt the user to select an option
    extra_info_id = await zSingleSelectView(select_list, None, "Choose Extra Info Type..").prompt(interaction)

    extra_info_type = get_extra_info_type(extra_info_id)
    extra_info_name = "" if extra_info_type is None else extra_info_type.name

    # Check if we're creating a new assignment or removing an existing one
    if check_category_assignment_exists(extra_info_id, category.id):
        # Remove the assignment
        delete_category_assignment(extra_info_id, category.id)
        await send_message(interaction, f"Extra Info Type `{extra_info_name}` removed from category `{category.name}`")
    else:
        # Create a new assignment
        assignment = AsyncRaceExtraInfoAssignment(info_type_id=extra_info_id, category_id=category.id)
        try:
            assignment.save()
        except:
            await send_message(interaction, "**Error** Failure saving extra info assignment.")
            return
        await send_message(interaction, f"Extra Info Type `{extra_info_name}` added to category `{category.name}`")

########################################################################################################################
async def category_display_raw_submit_info(interaction, category):
    # Prompt for how many races we want to query from
    num_races = await prompt_for_value(interaction, "How many races would you like to search?", "# of Races", 1)
    try:
        num_races = int(num_races)
    except:
        await send_message(interaction, "Number of races must be a valid integer, defaulting to 1")
        num_races = 1

    # Create a select list with the extra info types
    cat_assignments = get_category_extra_info_assignments(category.id)
    select_list = [
        nextcord.SelectOption(label="Finish Time", value=-1, description="Finish Time"),
        nextcord.SelectOption(label="Comment", value=-2, description="Comment")]
    for a in cat_assignments:
        select_list.append(nextcord.SelectOption(label=a.info_type_id.name, value=a.info_type_id.id, description=a.info_type_id.description))

    # Prompt the user to select which info types to include
    selected_info_types = await zMultiSelectView(select_list, len(select_list), None, "Choose Info Fields to include...").prompt(interaction)

    await send_message(interaction, "Fetching data, this may take a minute. Please wait...")

    # Get the extra infos for the selected list
    info_types = {}
    for s in selected_info_types:
        if s == -1 or s == -2:
            info_types[s] = None
        else:
            info_types[s] = get_extra_info_type(s)

    # Get the list of races, it comes pre-sorted by date so we can just slice the full list
    races = list(get_category_races(category.id))[:num_races]
    
    # Walk through the race submissions, one race at a time, collecting the data
    raw_data_dict = {}
    for r in races:
        submissions = get_sorted_race_submissions(r.id)
        for s in submissions:
            for t in selected_info_types:
                if t == -1:
                    if t in raw_data_dict:
                        if s.user_id in raw_data_dict[t]:
                            raw_data_dict[t][s.user_id].append(s.finish_time)
                        else:
                            raw_data_dict[t][s.user_id] = [s.finish_time]
                    else:
                        raw_data_dict[t] = {s.user_id: [s.finish_time]}
                elif t == -2:
                    if s.comment is not None and s.comment != "":
                        if t in raw_data_dict:
                            if s.user_id in raw_data_dict[t]:
                                raw_data_dict[t][s.user_id].append(s.comment)
                            else:
                                raw_data_dict[t][s.user_id] = [s.comment]
                        else:
                            raw_data_dict[t] = {s.user_id: [s.comment]}
                else:
                    info = get_extra_info(s.id, t)
                    if info is not None:
                        if t in raw_data_dict:
                            if s.user_id in raw_data_dict[t]:
                                raw_data_dict[t][s.user_id].append(info.data)
                            else:
                                raw_data_dict[t][s.user_id] = [info.data]
                        else:
                            raw_data_dict[t] = {s.user_id: [info.data]}

    # Print it all out grouped by type
    msg = ""
    for t in raw_data_dict:
        info_type = info_types[t]
        if info_type is None:
            text = "Finish Time" if t == -1 else "Comment"
            msg += f"**{text}**\n"
        else:
            msg += f"**{info_type.name}**\n"
        for u in raw_data_dict[t]:
            user = await get_user_from_interaction(interaction, u)
            for d in raw_data_dict[t][u]:
                if user is None:
                    msg += f"Unknown User > {d}\n"
                else:
                    msg += f"{get_user_name_str(user.id, user)} > {d}\n"
    
    # Finally display it to the user
    await send_message(interaction, msg)
            

########################################################################################################################
async def category_set_thumbnail(interaction, category):
    thumbnail_url = await prompt_for_value(interaction, "Enter Thumbnail URL", "URL", category.thumbnail_url)
    if thumbnail_url is None or thumbnail_url == "":
        category.thumbnail_url = None
        category.save()
        await send_message(interaction, "Removed category thumbnail")
    elif validators.url(thumbnail_url):
        category.thumbnail_url = thumbnail_url
        category.save()
        await send_message(interaction, "Category thumbnail updated")
    else:
        await send_message(interaction, "Invalid URL")

########################################################################################################################
async def category_misc_toggles(interaction, category):
    # Build the list of toggle fields
    toggle_list = []
    toggle_list.append(get_ping_assigned_field(category))
    toggle_list.append(get_remove_category_leaderboard_field(category))
    toggle_list.append(get_leaderboard_type_toggle_field(category))
    toggle_list.append(get_category_active_toggle_field(category))
    toggle_list.append(get_category_pin_recent_toggle_field(category))
    toggle_list.append(get_category_allow_completed_submit_toggle_field(category))
    toggle_list.append(get_category_activate_new_races_toggle_field(category))
    
    # Get extra info assignments for this category
    extra_infos = get_category_extra_info_assignments(category.id)
    for a in extra_infos:
        toggle_list.append(get_extra_info_toggle_field(a))

    # Create and start the menu
    menu = zToggleButtonMenu(toggle_fields=toggle_list,
                             title="Category Misc Configuration",
                             description=ToggleMiscDescription)
    await menu.start(interaction=interaction)

########################################################################################################################
def get_leaderboard_type_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_leaderboard_type,
        payload=category,
        button_style=get_leaderboard_type_button_style(category.leaderboard_type),
        custom_id=toggle_leaderboard_id,
        emoji=LeaderboardEmoji,
        embed_field=EmbedField(name=f"{LeaderboardEmoji} - Leaderboard Type",
                               value=RaceLeaderboardType.to_str(category.leaderboard_type),
                               inline=False))

########################################################################################################################
def get_category_active_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_active,
        payload=category,
        button_style=active_field_button_style(category.leaderboard_type),
        custom_id=toggle_category_active_id,
        emoji=EyesEmoji,
        embed_field=EmbedField(name=f"{EyesEmoji} - Category Visibility",
                               value=active_field_to_str(category.active),
                               inline=False))

########################################################################################################################
def get_category_pin_recent_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_pin_recent,
        payload=category,
        button_style=bool_field_button_style(category.pin_recent_race),
        custom_id=toggle_category_pin_recent_id,
        emoji=PinEmoji,
        embed_field=EmbedField(name=f"{PinEmoji} - Pin Most Recent Race",
                               value=bool_field_to_str(category.pin_recent_race),
                               inline=False))

########################################################################################################################
def get_category_allow_completed_submit_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_allow_completed_submit,
        payload=category,
        button_style=bool_field_button_style(category.allow_completed_submit),
        custom_id=toggle_category_allow_completed_submit_id,
        emoji=TimeEmoji,
        embed_field=EmbedField(name=f"{TimeEmoji} - Allow Submissions on Completed Races",
                               value=bool_field_to_str(category.allow_completed_submit),
                               inline=False))

########################################################################################################################
def get_category_activate_new_races_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_activate_new_races,
        payload=category,
        button_style=bool_field_button_style(category.activate_new_races),
        custom_id=toggle_category_activate_new_races_id,
        emoji=ChangeStateEmoji,
        embed_field=EmbedField(name=f"{ChangeStateEmoji} - Auto-Activate New Races",
                               value=bool_field_to_str(category.activate_new_races),
                               inline=False))

########################################################################################################################
def get_ping_assigned_field(category):
    return ToggleField(
        toggle_func=category_ping_assigned_racers,
        payload=category,
        button_style=nextcord.ButtonStyle.blurple,
        custom_id=category_ping_assigned_id,
        emoji=AssignEmoji,
        embed_field=EmbedField(name=f"{AssignEmoji} - Ping Assigned",
                               value="Button will post a message pinging all assigned racers to active races in this category.",
                               inline=False))

########################################################################################################################
def get_remove_category_leaderboard_field(category):
    return ToggleField(
        toggle_func=category_remove_channel_leaderboard,
        payload=category,
        button_style=nextcord.ButtonStyle.blurple,
        custom_id=remove_category_leaderboard_id,
        emoji=DeleteEmoji,
        embed_field=EmbedField(name=f"{DeleteEmoji} - Remove Leaderboard",
                               value="Button will remove any leaderboard channel assignment and delete leaderboard messages.",
                               inline=False))

########################################################################################################################
def get_extra_info_toggle_field(assignment):
    emoji = get_random_emoji()
    return ToggleField(
        toggle_func=toggle_required_extra_info,
        payload=assignment,
        button_style=required_field_button_style(assignment.required),
        custom_id=f"extra_info_toggle_{assignment.info_type_id.name}",
        emoji=emoji,
        embed_field=EmbedField(name=f"{emoji} - Submit Info: {assignment.info_type_id.name}",
                               value=required_field_to_str(assignment.required),
                               inline=False))

########################################################################################################################
# Race Menu Functions
########################################################################################################################
async def create_edit_race_command(interaction, payload):
    await defer(interaction)

    if not user_is_mod(interaction.guild, interaction.user):
        await send_message(interaction, "You must be a race moderator to use this command.")
        return

    # Get a list of races
    select_list = get_race_select_list(interaction.guild_id)
    
    # Add the option for creating a new race to the front of the list
    select_list.insert(0, nextcord.SelectOption(label="Create New...", value=0, description="Create a new race."))
    
    # Prompt the user to select an option
    view = zSingleSelectView(select_list, create_edit_race, "Choose Race..")
    await send_message(interaction, view=view)

async def create_edit_race(race_id, interaction):
    if race_id == 0 or race_id is None:
        select_list = get_category_select_list(interaction.guild_id)
        # If there's only one category then no need to prompt the user to select one
        if len(select_list) == 1:
            await add_race(select_list[0].value, interaction)
        else:
            # Prompt the user to select a category for the race, then send the add race modal
            await send_message(interaction, view=zSingleSelectView(get_category_select_list(interaction.guild_id),
                                                                add_race,
                                                                "Select Race Category"))
    else:
        await send_race_menu(interaction, race_id)

async def add_race(category_id, interaction):
    modal = zRaceAddEditModal(interaction.guild_id, category_id)
    await interaction.response.send_modal(modal)
    # Once the modal is done, get the race to send the race edit menu
    await modal.wait()
    race_id = modal.race.id
    await send_race_menu(interaction, race_id)

########################################################################################################################
async def race_edit_core(interaction, race):
    # Only allow edit of race info if there are NO submissions and it is inactive
    has_submissions = race_has_submissions(race.id)
    if has_submissions:
        await send_message(interaction, "Cannot edit race info because this race already has submissions.") 
        return
    
    if race.state != RaceState.Inactive:
        await send_message(interaction, "Cannot edit race info because this race is not inactive.")
        return
    
    modal = zRaceAddEditModal(race.server_id.id, race.category_id.id, race=race)
    await interaction.response.send_modal(modal)

########################################################################################################################
async def race_delete(interaction, race):
    await defer(interaction)

    # We can only delete a race if it's inactive and has no submissions
    has_submissions = race_has_submissions(race.id)
    if has_submissions:
        await send_message(interaction, "Cannot delete this race because it has submissions.") 
        return
    
    if race.state != RaceState.Inactive:
        await send_message(interaction, "Cannot delete this race because it is not inactive.")
        return
    
    # First delete any extra info assignments
    extra_info_assignments = get_race_extra_info_assignments(race.id)
    for a in extra_info_assignments:
        a.delete_instance()
    
    # Then delete the race
    race_id = race.id
    race.delete_instance()
    await send_message(interaction, f"Race ID {race_id} has been deleted.")

########################################################################################################################
async def prompt_for_race_state(interaction, race):
    # Query for the new race state
    select_list = copy.deepcopy(RaceState.SelectOptionList)
    for s in select_list:
        if s.value == race.state:
            s.default = True
            break

    new_state = await zSingleSelectView(select_list, None, "Choose new state...").prompt(interaction)
    return new_state

########################################################################################################################
async def race_change_state(interaction, race, new_state=None, confirmed: bool=None):
    if new_state is None:
        new_state = await prompt_for_race_state(interaction, race)

    # Do some sanity checks of the new state
    if new_state == RaceState.Inactive:
        # If the new state is inactive, make sure there are no submissions
        if race_has_submissions(race.id):
            await send_message(interaction, "Cannot change state to Inactive because there are submissions.")
            return
    elif new_state == RaceState.Active:
        if race.state == RaceState.Completed:
            # For categories that have points, we can't go from completed to active
            if race.category_id.points_type != PointsType.NoScoring:
                await send_message(interaction, "Cannot change state to Active because the race has already been scored.")
                return
    elif new_state == RaceState.Completed:
        # If there are no submissions, confirm that the user meant to select `Completed`` and not `Inactive`
        if race_has_submissions(race.id) == False:
            if confirmed is None:
                confirmed = await zConfirmMenu("There are no submissions for this race, do you want to change to 'Inactive' instead?").prompt(interaction)
            if confirmed:
                new_state = RaceState.Inactive
        else:
            # If the race has assigned racers and not all have submitted, confirm that the user wants to change to `Completed`
            racers = get_assigned_racers(race.id)
            all_submitted = True
            for r in racers:
                submission = get_race_submission(r.user_id, race.id)
                if submission is None:
                    all_submitted = False
                    break
            if not all_submitted:
                if confirmed is None:
                    confirmed = await zConfirmMenu("Not all assigned racers have submitted, do you want to change to 'Completed' anyway?").prompt(interaction)
                if not confirmed:
                    await send_message(interaction, "Cancelled")
                    return
    # Now that all checks are done, save the new race state
    race.state = new_state
    race.save()
    
    if new_state == RaceState.Active:
        await handle_activate_race(interaction, race)
    elif new_state == RaceState.Completed:
        # If the new state is completed, score the race
        score_race(race)

        # Then update the category and/or race leaderboards
        await update_category_leaderboard(interaction, race)
        await update_race_leaderboard(interaction, race)
    
    await send_message(interaction, f"Race {race.id} state changed to {RaceState.to_str(new_state)}")

########################################################################################################################
async def race_pin(interaction, race):
    await defer(interaction)

    # Ask for the channel to pin the race to
    channel = await prompt_for_channel(interaction)
    if channel is None:
        return

    # Delete any existing race info messages
    msg_list = get_messages_by_race_id(race.id, RaceMessageType.RaceInfo)
    if msg_list is not None:
        for m in msg_list:
            if m.message_id is not None:
                await delete_message(get_server_from_interaction(interaction), m.id)

    # Then post the new race info message
    succcess = await pin_race_info(channel.id, race, interaction)
    if succcess:
        await send_message(interaction, f"Race #{race.id} pinned to channel ID {channel.name}")
    else:
        await send_message(interaction, f"**ERROR** Failed to pin Race #{race.id} to channel ID {channel.name}")

########################################################################################################################
async def race_edit_submit_role(interaction, race):
    await defer(interaction)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)
    logging.info(f"{get_user_name_str(interaction.user.id, interaction.user)} selected submit role: {selected_role} for race {race.id}")
    race.submission_role = selected_role
    race.save()
    await send_message(interaction, "Submit Role Saved")

########################################################################################################################
async def race_assign_racer(interaction, race):
    # Racers can only be assigned when in the inactive state
    if race.state != RaceState.Inactive:
        await send_message(interaction, "Can only assign racers in the `Inactive` state.")
    
    # Ask the user if they want to assign a specific user or a role
    select_list = [
        nextcord.SelectOption(label="User", value=1, description="Assign a specific user"),
        nextcord.SelectOption(label="Role", value=2, description="Assign all users with a specific role")
    ]
    assign_type = await zSingleSelectView(select_list, None, "Choose Assignment Type...").prompt(interaction)

    if assign_type == 1:
        # Prompt for the user to assign, removing already assigned racers
        user = await zUserSelectView(None).prompt(interaction)
    
        # Create a race assignment for this user
        assign_racer(user_id=user.id, race_id=race.id)
        await send_message(interaction, f"User {get_user_name_str(user.id, user)} assigned")
    elif assign_type == 2:
        # Prompt for the role to assign
        role_id = await prompt_for_role(interaction)
        if role_id is None:
            await send_message(interaction, "**ERROR** - No role selected, cancelled assignment")
            return
        
        role = interaction.guild.get_role(role_id)
        if role is None:
            await send_message(interaction, "**ERROR** - Role not found, cancelled assignment")
            return

        # Create an assignment for each member who has the selected role
        for m in role.members:
            assign_racer(user_id=m.id, race_id=race.id)
        await send_message(interaction, "Role assignment complete")
    else:
        await send_message(interaction, "**ERROR** - Unknown option selected, cancelled assignment")
        return
    
########################################################################################################################
async def race_edit_submission(interaction, race):
    if race.state == RaceState.Inactive:
        await send_message(interaction, "Cannot create submissions for an Inactive race.")
        return
    
    # Get a list of submissions
    # Get a list of submissions for this race
    submissions = get_sorted_race_submissions(race.id)

    # Create a select list from the submissions
    select_list = [nextcord.SelectOption(label="Create New...", value=-1, description="Create a new submission"),
                   nextcord.SelectOption(label="Cancel...", value=0, description="Cancel the operation")]
    if submissions is not None:
        for s in submissions:
            user = await get_user_from_interaction(interaction, s.user_id)
            user_name = get_user_name_str(s.user_id, user)
            select_list.append(nextcord.SelectOption(label=f"{user_name} - {s.finish_time}", value=s.id, description=f"{user_name} - {s.finish_time}"))
    
    # Prompt the user to select a submission
    view = zSingleSelectView(select_list, on_select_edit_submission, "Choose Submission To Edit..", payload=race.id)
    await send_message(interaction, view=view)

async def on_select_edit_submission(select_data, interaction):
    submission_id = select_data[0]
    race_id = select_data[1]
    if submission_id == 0:
        await send_message(interaction, "Cancelled")
        return
    elif submission_id == -1:
        # Ask which racer we're creating a submission for
        await send_message(interaction, view=zUserSelectView(on_select_user_edit_submission, placeholder="Choose racer to submit for...", payload=race_id))
    else:
        # Get the submission and send the submission edit modal
        submission = get_race_submission_by_id(submission_id)
        if submission is not None:
            # Send the submission edit modal
            submit_handler = zRaceSubmitHandler(submission.race_id, submission, include_points=True)
            await submit_handler.send_submit_modal(interaction)
        
async def on_select_user_edit_submission(select_data, interaction):
    user = select_data[0]
    race_id = select_data[1]

    if user is None:
        await send_message(interaction, "Cancelled")
        return
    
    # If this is an assigned race, make sure the selected user is assigned to it
    if is_assigned_race(race_id):
        assignment = get_race_assignment(user.id, race_id)
        if assignment is None:
            await send_message(interaction, "Cancelled. Selected user is not assigned to this race and the race is not open.")
            return
    
    # Check if the selected user already has a submission to avoid duplicates
    submission = get_race_submission(user.id, race_id)
    
    submit_handler = zRaceSubmitHandler(race_id, submission, include_points=True, user_id=user.id)
    await submit_handler.send_submit_modal(interaction)
    pass

########################################################################################################################
async def race_schedule_op(interaction, race):
    # Prompt the user for the date/time
    now_ts = int(time.time())
    timestamp = await prompt_for_value(interaction,
                                       "Enter Date/Time",
                                       "Date/Time in Discord Timestamp Format",
                                       now_ts)
    timestamp = int(timestamp)
    
    # Validate the timestamp. Time must not be in the past and no more than 2 days in the future
    if timestamp < now_ts:
        await send_message(interaction, "Cannot schedule a time in the past.")
        return
    elif timestamp > now_ts + (60*48):
        await send_message(interaction, "Cannot schedule a time more than 2 days in the future.")
        return
    else:
        # Prompt the user for the new state
        new_state = await prompt_for_race_state(interaction, race)
        
        # Create a thread to wait the appropriate amount of time and then call the race state update
        schedule_thread = threading.Thread(target=asyncio.run, args=(schedule_race_state_change(interaction, race, timestamp, new_state),))
        schedule_thread.start()

########################################################################################################################
async def schedule_race_state_change(interaction, race, end_timestamp, new_state):
    # Sleep until the timestamp in 1 minute increments to avoid accumulating sleep drift
    while int(time.time()) < end_timestamp:
        delta = (end_timestamp - int(time.time())) + 1
        if delta < 60:
            await asyncio.sleep(delta)
        else:
            await asyncio.sleep(60)

    # Now execute the race state change
    await race_change_state(interaction, race, new_state=new_state, confirmed=True)

########################################################################################################################
async def race_misc_toggles(interaction, race):
    # Build the list of toggle fields
    toggle_list = []
    toggle_list.append(get_remove_race_leaderboard_field(race))
    
    # Get extra info assignments for this category
    extra_infos = get_race_extra_info_assignments(race.id)
    for a in extra_infos:
        toggle_list.append(get_extra_info_toggle_field(a))

    # Create and start the menu
    menu = zToggleButtonMenu(toggle_fields=toggle_list,
                             title="Race Misc Configuration",
                             description=ToggleMiscDescription)
    await menu.start(interaction=interaction)

########################################################################################################################
def get_remove_race_leaderboard_field(race):
    return ToggleField(
        toggle_func=race_remove_channel_leaderboard,
        payload=race,
        button_style=nextcord.ButtonStyle.blurple,
        custom_id=remove_race_leaderboard_id,
        emoji=DeleteEmoji,
        embed_field=EmbedField(name=f"{DeleteEmoji} - Remove Leaderboard",
                               value="Button will remove any leaderboard channel assignment and delete leaderboard messages.",
                               inline=False))
        

########################################################################################################################
async def create_edit_extra_info(interaction, payload):
    await defer(interaction)

    if not user_is_mod(interaction.guild, interaction.user):
        await send_message(interaction, "You must be a race moderator to use this command.")
        return

    # Get a list of extra info types
    select_list = get_extra_info_type_select_list(interaction.guild_id)
    
    # Add the option for creating a new type to the front of the list
    select_list.insert(0, nextcord.SelectOption(label="Create New...", value=0, description="Create a new info type."))
    
    # Prompt the user to select an option
    view = zSingleSelectView(select_list, on_select_create_edit_extra_info, "Choose Extra Info..")
    await send_message(interaction, view=view)

async def on_select_create_edit_extra_info(extra_info_id, interaction):
    if extra_info_id == 0:
        extra_info_id = None
    # Create a new extra info type
    modal = zExtraInfoTypeAddEditModal(extra_info_id)
    await interaction.response.send_modal(modal)

########################################################################################################################
async def mod_menu_help(interaction, payload):
    if not user_is_mod(interaction.guild, interaction.user):
        await send_message(interaction, "You must be a race moderator to use this command.")
        return
    
    # Create and display the help button menu
    title = "Racer Moderation Help"
    description = f"Use the buttons below to view help information for the various racer moderation functions."
    footer = "For questions or support not covered in the help topics, please contact a bot admin."
    menu = zButtonMenu(None, RaceModerationHelpMenuItems, use_channel=False, title=title, description=description, footer=footer)
    await menu.start(interaction=interaction, ephemeral=True)
    
########################################################################################################################
async def race_assign_extra_info(interaction, race):
    # Get a list of extra info types
    select_list = get_extra_info_type_select_list(interaction.guild_id)

    # Update the labels for the items that are already assigned
    for s in select_list:
        if check_race_assignment_exists(s.value, race.id):
            s.label = f"✅ {s.label}"

    # Prompt the user to select an option
    extra_info_id = await zSingleSelectView(select_list, None, "Choose Extra Info Type..").prompt(interaction)

    extra_info_type = get_extra_info_type(extra_info_id)
    extra_info_name = "" if extra_info_type is None else extra_info_type.name
    
    # Check if we're creating a new assignment or removing an existing one
    if check_race_assignment_exists(extra_info_id, race.id):
        # Remove the assignment
        delete_race_assignment(extra_info_id, race.id)
        await send_message(interaction, f"Extra Info Type `{extra_info_name}` removed from race ID `{race.id}`")
    else:
        # Create a new assignment
        assignment = AsyncRaceExtraInfoAssignment(info_type_id=extra_info_id, race_id=race.id)
        try:
            assignment.save()
        except:
            await send_message(interaction, "**Error** Failure saving extra info assignment.")
            return
        await send_message(interaction, f"Extra Info Type `{extra_info_name}` added to race ID `{race.id}`")

########################################################################################################################
async def show_category_help(interaction, payload):
    await send_message(interaction, CategoryHelpText)

########################################################################################################################
async def show_category_scoring_help(interaction, payload):
    await send_message(interaction, CategoryScoringHelpText)

########################################################################################################################
async def show_race_help(interaction, payload):
    await send_message(interaction, RaceHelpText)

########################################################################################################################
async def show_extra_info_help(interaction, payload):
    await send_message(interaction, ExtraInfoHelpText)

########################################################################################################################
# Racer Info Menu Functions
########################################################################################################################
async def racer_info_stats(interaction, payload):
    await show_racer_stats(interaction, interaction.user.id)

########################################################################################################################
async def racer_info_show_open_races(interaction, payload):
    # Get the list of active open races
    races = get_open_races(interaction.guild_id)
    races = list(filter(lambda r: r.state == RaceState.Active, races))

    if len(races) > 0:
        # Display it as a paginated list
        race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id, use_inline_fields=True),
                                            style=ButtonStyle.secondary,
                                            timeout=None)
        
        await race_list_menu.start(interaction=interaction, ephemeral=True)
    else:
        await send_message(interaction, "No open races found.")


########################################################################################################################
async def racer_info_show_assigned_races(interaction, payload):
    # Get the list of assigned races
    races = get_assigned_races(interaction.user.id, interaction.guild_id, states=[RaceState.Active])

    if races is None or len(races) == 0:
        await send_message(interaction, "You currently have no assigned races.")
        return
    
    # Display it as a paginated list
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id),
                                        style=ButtonStyle.secondary,
                                        timeout=None)
    
    await race_list_menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def racer_info_show_categories(interaction, payload):
    categories = get_categories(interaction.guild_id)

    if categories is None or len(categories) == 0:
        await send_message(interaction, "No categories found for this server.")
        return
    
    # Display it as a paginated list
    category_list_menu = zCategoryListMenuPages(source=zCategoryListPageSource(categories, interaction.guild_id),
                                                style=ButtonStyle.secondary,
                                                timeout=None)
    
    await category_list_menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def racer_info_view_other_racer(interaction, payload):
    selected_user = await zUserSelectView(None).prompt(interaction)

    if selected_user is not None:
        await show_racer_stats(interaction, selected_user.id)
    else:
        await send_message(interaction, "Cancelled")

########################################################################################################################
async def racer_info_show_completed_races(interaction, payload):
    # Get the list of completed races
    races = get_completed_races(interaction.user.id, interaction.guild_id)

    if races is None or len(races) == 0:
        await send_message(interaction, "No completed races found.")
        return
    
    # Display it as a paginated list
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id),
                                        style=ButtonStyle.secondary,
                                        timeout=None)
    
    await race_list_menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def show_racer_info_help(interaction, payload):
    await send_message(interaction, RacerInfoHelpText)

########################################################################################################################
# Other Menu Functions
########################################################################################################################
async def send_moderator_menu(interaction, channel, footer=None):
    title = f"Async Race Moderation"
    description = f"Use the buttons below to manage aync races and categories. Descriptions of the functions are below."
    if footer is None:
        footer = "For questions or issues that are not covered by the help topics, please contact a bot admin."
    menu = zButtonMenu(None, ModeratorMenuItems, use_channel=True, title=title, description=description, footer=footer)
    await menu.start(interaction=interaction, channel=channel, ephemeral=False)
    return menu.message

########################################################################################################################
async def send_racer_menu(interaction, channel, footer=None):
    title = f"Async Race Dashboard"
    description = f"Use the buttons below to discover races, view your stats and more."
    if footer is None:
        footer = "For questions or issues please contact a race moderator or bot admin."
    menu = zButtonMenu(None, RacerInfoButtonMenuItems, use_channel=True, title=title, description=description, footer=footer)
    await menu.start(interaction=interaction, channel=channel, ephemeral=False)
    return menu.message

########################################################################################################################
async def send_category_menu(interaction, category_id):
    category = get_category(category_id)
    if category is None:
        return

    title = f"`{category.name}` Category Management"
    description = f"Use the buttons below to manage the `{category.name}` category.\nDescription: `{category.description}`"
    menu = zButtonMenu(category, CategoryButtonMenuItems, use_channel=False, title=title, description=description)
    await menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def send_race_menu(interaction, race_id):
    race = get_race(race_id)
    if race is None:
        logging.info(f"**ERROR** Race with ID {race_id} not found")
        return

    title = f"Race Management for Race ID {race.id}"
    description = f"Use the buttons below to manage Race ID {race.id} category.\nDescription:\n`{race.description}`"
    footer = "For more information about race management, use the commands in the Race Management Info embed"
    menu = zButtonMenu(race, RaceButtonMenuItems, use_channel=False, title=title, description=description)
    await menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def prompt_for_value(interaction, title, label, default_value):
    modal = zModal({label: nextcord.ui.TextInput(label=label, custom_id=label, required=True, default_value=default_value)},
                   None,
                   title)
    await interaction.response.send_modal(modal)
    await modal.wait()
    for c in modal.children:
        if c.custom_id == label:
            return c.value

########################################################################################################################
async def prompt_for_role(interaction, placeholder="Choose Role..."):
    server = get_server_from_interaction(interaction)
    role_list = get_role_select_list(server)
    
    selected_role = await zSingleSelectView(role_list, None, placeholder).prompt(interaction)
    
    return None if selected_role == 0 else selected_role

########################################################################################################################
async def prompt_for_channel(interaction, placeholder="Choose Channel..."):
    server = get_server_from_interaction(interaction)
    channel_list = await get_permitted_channel_select_list(interaction.client.user.id, server)
    
    selected_channel_id = await zSingleSelectView(channel_list, None, placeholder).prompt(interaction)
    if selected_channel_id == 0:
        await send_message(interaction, "**ERROR** Could not fetch selected channel. Please contact a bot admin.")
        return None
    else:
        return interaction.guild.get_channel(selected_channel_id)

########################################################################################################################
async def show_race_details(interaction, race_id):
    race = get_race(race_id)
    if race is None:
        await send_message(interaction, "**ERROR** Could not find race data. Please notify a bot admin")
        return
    # If this is an assigned race and the user has not viewed the race info before, confirm they are ready
    if is_assigned_race(race_id):
        assignment = get_race_assignment(interaction.user.id, race_id)
        if assignment is not None and assignment.seed_time is None:
            confirmed = await zConfirmMenu(ConfirmSeedText).prompt(interaction)
            if confirmed:
                assignment.seed_time = datetime.now()
                assignment.save()
            else:
                await send_message(interaction, "Cancelled")
                return

    seed_embed = get_race_info_message(race)
    zRaceInfoButtonView.add_static_embed_fields(seed_embed)
    await send_message(interaction, view=zRaceInfoButtonView(race.id), embed=seed_embed)

########################################################################################################################
async def show_submission_details(interaction, submission_id):
    submission = get_race_submission_by_id(submission_id)
    if submission is None:
        await send_message(interaction, "**ERROR** Could not find submission data. Please notify a bot admin")
        return
    
    race_id = submission.race_id.id
    user = await get_user_from_interaction(interaction, submission.user_id)
    title=f"{get_user_name_str(submission.user_id, user)} Submission for Race ID #{race_id}"
    num_submissions = get_num_submissions(race_id)
    race_submissions = get_sorted_race_submissions(race_id)
    place_ordinal = 0
    for i, s in enumerate(race_submissions):
        if s.id == submission_id:
            place_ordinal = i + 1
            break
    place_str = get_place_str(place_ordinal)
    description = f"Race {race_id} - {submission.race_id.description}\nSubmitted: {submission.submit_datetime}\n{place_str} out of {num_submissions} racers"
    embed = nextcord.Embed(title=title, description=description, color=0x00ff00)

    embed.add_field(name="Finish Time", value=submission.finish_time)
    if not is_value_empty(submission.comment):
        embed.add_field(name="Comment", value=submission.comment, inline=False)
    if not is_value_empty(submission.points):
        embed.add_field(name="Points", value=format_points_str(submission.points), inline=False)
    
    # Get extra info types assigned to this race
    extra_info_assignments = AsyncRaceExtraInfoAssignment.select().where(AsyncRaceExtraInfoAssignment.race_id == race_id)
    logging.info("--: Getting Extra Info Assignments")
    for a in extra_info_assignments:
        # Lookup the extra infos for this submission and add them to the table
        info = get_extra_info(submission.id, a.info_type_id)
        if info is not None:
            info_type = get_extra_info_type(a.info_type_id)
            if not is_value_empty(info.data):
                embed.add_field(name=info_type.name, value=info.data, inline=False)
            else:
                logging.info("--: Data was empty")
        else:
            logging.info("--: Info was null")

    await send_message(interaction, embed=embed)

########################################################################################################################
async def show_racer_stats(interaction, user_id):
    server = get_server_from_interaction(interaction)
    user = await server.fetch_member(user_id)
    user_name = get_user_name_str(user_id, user)
    
    # Collect the core stats
    races = get_completed_races(user_id, interaction.guild_id)
    total_races = 0
    total_wins = 0
    total_podiums = 0
    user_races = []
    cat_count = dict()
    for r in races:
        user_submission = get_race_submission(user_id, r.id)
        is_user_race = False
        if user_submission is not None:
            total_races += 1
            user_races.append(r)

            submissions = get_sorted_race_submissions(r.id)
            if len(submissions) > 0:
                if submissions[0].user_id == user_id:
                    total_wins += 1
                    total_podiums += 1

                if len(submissions) >= 3:
                    if submissions[1].user_id == user_id or submissions[2].user_id == user_id:
                        total_podiums += 1
                        
                if r.category_id.name not in cat_count:
                    cat_count[r.category_id.name] = 1
                else:
                    cat_count[r.category_id.name] += 1

    highest_count = 0
    highest_count_name = 0
    for c in cat_count:
        if cat_count[c] > highest_count:
            highest_count = cat_count[c]
            highest_count_name = c
    
    most_raced_category = highest_count_name

    # Get the 1v1 record
    if interaction.user.id == user_id:
        # If we're getting stats for the `My Stats` button we want 1v1 record against everyone
        opponent_id = None
        viewing_self = True
    else:
        # If we're viewing someone else's stats we want to show the interaction users record against the selected user
        opponent_id = user_id
        viewing_self = False
    one_v_one_wins, one_v_one_losses, one_v_one_ties = get_one_v_one_record(interaction.user.id, interaction.guild_id, opponent_id=opponent_id)
    one_v_one_label = "1v1 Record" if viewing_self else f"{get_user_name_str(interaction.user.id, interaction.user)} 1v1 Record vs {user_name}"
    one_v_one_value = f"{one_v_one_wins} - {one_v_one_losses} - {one_v_one_ties}"

    # Store the stats as embed fields
    static_embed_fields = [
        EmbedField("---------------------------------", "**Core Stats**"),
        EmbedField("Total Races", str(total_races), inline=True),
        EmbedField("Race Wins", str(total_wins),inline=True),
        EmbedField("Podium Finishes", str(total_podiums),inline=True),
        EmbedField("Most Raced Category", most_raced_category, inline=True)]
    if one_v_one_wins > 0 or one_v_one_losses > 0 or one_v_one_ties > 0:
        static_embed_fields.append(EmbedField(one_v_one_label, one_v_one_value, inline=False))
    static_embed_fields.append(EmbedField("---------------------------------", "**Recent Races**"))
    
    # Display the core stats and recent races as a paginated list
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(user_races, interaction.guild_id, use_inline_fields=False, static_embed_fields=static_embed_fields, title=user_name, user_id=user_id),
                                        style=ButtonStyle.secondary,
                                        timeout=None)
    
    await race_list_menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def show_race_leaderboard(interaction, race_id):
    submissions = get_sorted_race_submissions(race_id)
    race = get_race(race_id)
    menu = zRaceLeaderboardMenuPages(source=zRaceLeaderboardPageSource(submissions, 
                                                                       interaction.guild_id,
                                                                       interaction.client,
                                                                       title=get_race_leaderboard_title(race_id),
                                                                       body_text=get_race_leaderboard_description(race_id)))
    await menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def post_channel_race_leaderboard(interaction, channel, race_id, bot_client, emojis, save_as_category_message=False):
    per_page=10
    submissions = get_sorted_race_submissions(race_id)

    title = get_race_leaderboard_title(race_id)
    body_text = get_race_leaderboard_description(race_id)
    race = get_race(race_id)

    if len(submissions) == 0:
        msg_text = f"**{title}**\n\n{body_text}\n\nNo submissions yet"
        msg = await channel.send(msg_text)
        if save_as_category_message:
            save_message(interaction.guild_id, channel.id, msg.id, category_id=race.category_id.id)
        else:
            save_message(interaction.guild_id, channel.id, msg.id, race_id=race_id)
        return
    
    num_pages = math.ceil(len(submissions) / per_page)
    race_id = submissions[0].race_id
    
    embed_list = []
    for p in range(0, num_pages):
        slice = submissions[p*per_page:(p+1)*per_page]
        embed = await get_race_leaderboard_embed(title, body_text, slice, p, per_page, bot_client)
        embed_list.append(embed)
    
    for e in embed_list:
        msg = await channel.send(embed=e)
        if save_as_category_message:
            logging.info(f"Saving race leaderboard {race_id} as a category message")
            save_message(interaction.guild_id, channel.id, msg.id, category_id=race.category_id.id)
        else:
            logging.info(f"Saving race leaderboard {race_id} as a race message")
            save_message(interaction.guild_id, channel.id, msg.id, race_id=race_id)

########################################################################################################################
async def race_edit_leaderboard_channel(interaction, race):
    await defer(interaction)

    # Prompt for the desired channel
    selected_channel = await prompt_for_channel(interaction)
    if selected_channel is None:
        return
    
    logging.info(f"{get_user_name_str(interaction.user.id, interaction.user)} selected leaderboard channel: {selected_channel.name} for race {race.id}")

    # Find any existing leaderboard message and remove it
    leaderboard_msg_list = get_messages_by_race_id(race.id)
    if leaderboard_msg_list is not None and len(leaderboard_msg_list) > 0:
        for m in leaderboard_msg_list:
            if m.message_id is not None:
                await delete_message(get_server_from_interaction(interaction), m.id)
    
    message_id = None
    if race.state != RaceState.Inactive and race_has_submissions(race.id):
        # posting the leaderboard to the new channel will save the message ID(s) to the DB
        await post_channel_race_leaderboard(interaction, selected_channel, race.id, interaction.client, get_emoji_list())
    else:
        # If the race hasn't started or has no submissions yet, we just save the channel and race ID
        msg = AsyncRaceMessage(server_id=race.server_id, channel_id=selected_channel.id, message_id=message_id, race_id=race.id)
        try:
            msg.save()
        except:
            await send_message(interaction, "**ERROR** Failure saving leaderboard channel.")
            return

    await send_message(interaction, "Category Leaderboard Channel Saved")

########################################################################################################################
async def post_channel_category_leaderboard(interaction, channel, category_id, bot_client):
    per_page = 8
    category = get_category(category_id)
    if category is None:
        await send_message(interaction, f"**ERROR** Fetching category with ID {category_id}. Please contact a bot admin.")
        return
    
    if category.leaderboard_type == RaceLeaderboardType.RecentRace:
        # Determine the most recent completed race
        race = get_most_recent_race(category_id)
        if race is None:
            await send_message(interaction, f"No active or completed races yet for category {category.name}")
        else:    
            await post_channel_race_leaderboard(interaction, channel, race.id, bot_client, get_emoji_list(), save_as_category_message=True)
    else:
        embed_list = await get_category_leaderboard_embed_list(category_id, per_page, bot_client)
        if embed_list is None or len(embed_list) == 0:
            msg = await channel.send(f"No points scored yet for category {category.name}. This is likely due to no completed races.")
            save_message(interaction.guild_id, channel.id, msg.id, category_id=category_id)
        else:
            for e in embed_list:
                msg = await channel.send(embed=e)
                save_message(interaction.guild_id, channel.id, msg.id, category_id=category_id)

########################################################################################################################
async def get_category_leaderboard_embed_list(category_id, per_page, bot_client):
    points_list = get_category_points(category_id)
    num_pages = math.ceil(len(points_list) / per_page)
    embed_list = []
    for p in range(0, num_pages):
        slice = points_list[p*per_page:(p+1)*per_page]
        title = get_category_leaderboard_title(category_id)
        body_text = get_category_leaderboard_description(category_id)
        embed = await get_category_leaderboard_embed(title, body_text, slice, p, per_page, bot_client)
        embed_list.append(embed)
    return embed_list

########################################################################################################################
async def show_category_leaderboard(interaction, category_id):
    category = get_category(category_id)
    if category is None:
        await send_message(interaction, f"**ERROR** Fetching category with ID {category_id}. Please contact a bot admin.")
        return
    
    if category.leaderboard_type == RaceLeaderboardType.RecentRace:
        # Determine the most recent completed race and show the leaderboard for it
        races = get_completed_races_by_category(category_id)
        await show_race_leaderboard(interaction, races[0].id)
    else:
        points_list = get_category_points(category_id)
        if points_list is None or len(points_list) == 0:
            await send_message(interaction, get_category_no_points_message(category.name))
            return
        
        menu = menus.ButtonMenuPages(source=zCategoryPointsLeaderboardPageSource(points_list, interaction.client))
        await menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
def get_leaderboard_type_button_style(leaderboard_type) -> nextcord.ButtonStyle:
    if leaderboard_type == RaceLeaderboardType.RecentRace:
        return nextcord.ButtonStyle.green
    else:
        return nextcord.ButtonStyle.blurple
    
########################################################################################################################
def required_field_button_style(required) -> nextcord.ButtonStyle:
    return nextcord.ButtonStyle.red if required else nextcord.ButtonStyle.grey

########################################################################################################################
def required_field_to_str(required) -> str:
    return "Required" if required else "Optional"

########################################################################################################################
def active_field_button_style(active) -> nextcord.ButtonStyle:
    return nextcord.ButtonStyle.green if active else nextcord.ButtonStyle.grey

########################################################################################################################
def active_field_to_str(active) -> str:
    return "Active" if active else "Inactive"

########################################################################################################################
def bool_field_button_style(active) -> nextcord.ButtonStyle:
    return nextcord.ButtonStyle.green if active else nextcord.ButtonStyle.grey

########################################################################################################################
def bool_field_to_str(bool_val) -> str:
    return "True" if bool_val else "False"

########################################################################################################################
async def toggle_category_leaderboard_type(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]
    
    # ToggleField payload is the category
    category = toggle_field.payload
    
    # Update the database based on the current value
    if category.leaderboard_type == RaceLeaderboardType.RecentRace:
        category.leaderboard_type = RaceLeaderboardType.Points
    else:
        category.leaderboard_type = RaceLeaderboardType.RecentRace
    category.save()

    # Then update the button style
    toggle_field.button_style = get_leaderboard_type_button_style(category.leaderboard_type)

    # Then update the embed field value
    toggle_field.embed_field.value = RaceLeaderboardType.to_str(category.leaderboard_type)
    logging.info(f"Category {category.name} leaderboard type toggled to {toggle_field.embed_field.value}")

    # Finally update the menu
    await update_menu_embed_field(menu, toggle_field)

########################################################################################################################
async def category_ping_assigned_racers(interaction, payload):
    # The button payload is the ToggleField
    menu = payload[0]
    toggle_field = payload[1]

    # ToggleField payload is the category
    category = toggle_field.payload

    # Ask what channel we should put the ping
    channel = await prompt_for_channel(interaction, placeholder="Choose Channel for Ping Message...")

    if channel is None:
        await send_message(interaction, "**ERROR** Could not fetch channel. Please contact a bot admin.")
        return

    # Get a list of active race assignments in this category
    assignments = get_active_category_assignments(category.id)

    msg = ""
    for a in assignments:
        user = await get_user_from_interaction(interaction, a.user_id)
        msg += f"{user.mention} "
    
    msg += f" You have been assigned to a new {category.name} race. Good luck!"
    await channel.send(msg)

########################################################################################################################
async def category_remove_channel_leaderboard(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]

    # ToggleField payload is the category
    category = toggle_field.payload

    # Find any existing leaderboard messages and remove them
    leaderboard_msg_list = get_messages_by_category_id(category.id)
    for m in leaderboard_msg_list:
        if m.message_id is not None:
            await delete_message(get_server_from_interaction(interaction), m.id)

    await send_message(interaction, f"Leaderboard channel removed for category {category.name}")

########################################################################################################################
async def race_remove_channel_leaderboard(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]

    # ToggleField payload is the race
    race = toggle_field.payload

    # Find any existing leaderboard messages and remove them
    leaderboard_msg_list = get_messages_by_race_id(race.id)
    for m in leaderboard_msg_list:
        if m.message_id is not None:
            await delete_message(get_server_from_interaction(interaction), m.id)

    await send_message(interaction, f"Leaderboard channel removed for race {race.id}")

########################################################################################################################
async def toggle_required_extra_info(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]

    # ToggleField payload is the extra info assignment
    assignment = toggle_field.payload

    assignment.required = not assignment.required
    assignment.save()

    # Then update the button style
    toggle_field.button_style = required_field_button_style(assignment.required)

    # Then update the embed field value
    toggle_field.embed_field.value = required_field_to_str(assignment.required)

    # Finally update the menu
    await update_menu_embed_field(menu, toggle_field)

########################################################################################################################
async def toggle_category_active(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]
    
    # ToggleField payload is the category
    category = toggle_field.payload

    category.active = not category.active
    category.save()

    # Then update the button style
    toggle_field.button_style = active_field_button_style(category.active)

    # Then update the embed field value
    toggle_field.embed_field.value = active_field_to_str(category.active)

    # Finally update the menu
    await update_menu_embed_field(menu, toggle_field)

########################################################################################################################
async def toggle_category_pin_recent(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]
    
    # ToggleField payload is the category
    category = toggle_field.payload

    category.pin_recent_race = not category.pin_recent_race
    category.save()

    # Then update the button style
    toggle_field.button_style = bool_field_button_style(category.pin_recent_race)

    # Then update the embed field value
    toggle_field.embed_field.value = bool_field_to_str(category.pin_recent_race)

    # Get the most recent active race for this category and either pin or unpin it depending on what was just toggled
    race = get_most_recent_race(category.id, include_completed=category.allow_completed_submit)
    
    if race is not None:
        if category.pin_recent_race:
            await pin_race_for_category(interaction, race)
        else:
            await remove_category_race_info_messages(interaction, race)

    # Finally update the menu
    await update_menu_embed_field(menu, toggle_field)

########################################################################################################################
async def toggle_category_allow_completed_submit(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]
    
    # ToggleField payload is the category
    category = toggle_field.payload

    category.allow_completed_submit = not category.allow_completed_submit
    category.save()

    # Then update the button style
    toggle_field.button_style = bool_field_button_style(category.allow_completed_submit)

    # Then update the embed field value
    toggle_field.embed_field.value = bool_field_to_str(category.allow_completed_submit)

    # Finally update the menu
    await update_menu_embed_field(menu, toggle_field)

########################################################################################################################
async def toggle_category_activate_new_races(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]
    
    # ToggleField payload is the category
    category = toggle_field.payload

    category.activate_new_races = not category.activate_new_races
    category.save()

    # Then update the button style
    toggle_field.button_style = bool_field_button_style(category.activate_new_races)

    # Then update the embed field value
    toggle_field.embed_field.value = bool_field_to_str(category.activate_new_races)

    # Finally update the menu
    await update_menu_embed_field(menu, toggle_field)

########################################################################################################################
async def update_menu_embed_field(menu, toggle_field: ToggleField):
    # Create a new embed copying the base data from the existing one
    embed = copy_embed(menu.embed)

    # Update the field and button style
    for i, f in enumerate(menu.embed.fields):
        if menu.toggle_fields[i].custom_id == toggle_field.custom_id:
            embed.add_field(name=toggle_field.embed_field.name, value=toggle_field.embed_field.value, inline=toggle_field.embed_field.inline)
            menu.children[i].style = toggle_field.button_style
        else:
            embed.add_field(name=f.name, value=f.value, inline=f.inline)
   
    # Tell the menu to update the message
    await menu.send_updated_message(embed)

########################################################################################################################
async def update_category_leaderboard(interaction, race):
    # Check if there are any category leaderboard messages
    msgs = get_messages_by_category_id(race.category_id.id)
    msgs = list(filter(lambda x: x.message_type is RaceMessageType.Leaderboard, msgs))

    # We can only update the leaderboard if there is a message stored in the DB indicating the saved channel
    if msgs is not None and len(msgs) > 0:
        # Extract the channel_id from the message and fetch the channel
        channel = interaction.guild.get_channel(msgs[0].channel_id)

        # Delete the existing messages
        for m in msgs:
            await delete_message(interaction.guild, m.id)

        # Post the updated leaderboard to the channel
        await post_channel_category_leaderboard(interaction, channel, race.category_id.id, interaction.client)

########################################################################################################################
async def update_race_leaderboard(interaction, race):
    if not race_has_submissions(race.id):
        # If there are no submissions yet then there's nothing to do
        return
    
    # Check if there are any race leaderboard messages
    msgs = get_messages_by_race_id(race.id, message_type=RaceMessageType.Leaderboard)
    
    if msgs is not None and len(msgs) > 0:
        # Extract the channel_id from the message and fetch the channel
        channel = interaction.guild.get_channel(msgs[0].channel_id)

        # Delete the existing messages
        for m in msgs:
            await delete_message(interaction.guild, m.id)

        # Post the updated leaderboard to the channel
        await post_channel_race_leaderboard(interaction, channel, race.id, interaction.client, get_emoji_list())
    else:
        logging.info(f"No race messages found in update_race_leaderboard")

    # If this is the most recent race in the category and the category leaderboard type is set to recent race,
    # update the category leaderboard
    if race.category_id.leaderboard_type == RaceLeaderboardType.RecentRace:
        recent_race = get_most_recent_race(race.category_id.id)
        if recent_race.id == race.id:
            await update_category_leaderboard(interaction, race)

########################################################################################################################
async def send_confirmed_race_announcement(interaction, confirmed, payload):
    race, msg_text = payload

    # If so, prompt the user for the desired message
    if confirmed:
        msg_text = await prompt_for_value(interaction, "Enter New Message (blank to cancel sending)", "Announcement Message", msg_text)

    # Prompt the user for the desired channel
    channel = await prompt_for_channel(interaction, "Choose Announcement Channel...")
    if channel is None:
        return

    # Finally post the message to the channel and save it to the DB
    msg = await channel.send(msg_text)
    save_message(interaction.guild_id, channel.id, msg.id, message_type=RaceMessageType.Announcement, category_id=race.category_id.id)

########################################################################################################################
async def send_race_announcement(interaction, race):
    msg_text = ""
    if race.category_id.create_role is not None:
        # Verify we have a valid role saved
        role = interaction.guild.get_role(race.category_id.create_role)
        if role is None:
            await send_message(interaction, f"**ERROR** Could not fetch stored category create role")
            return
        
        # Construct the default announcement message
        msg_text += f"Hey {role.mention}! "
    msg_text += f"A new {race.category_id.name} race has been created. Check it out and submit your time. GLHF!"

    # Ask the user if they want to make changes
    await send_message(interaction, 
                       msg = f"The following message will be sent:\n\n{msg_text}\n\nWould you like to edit the message?\n  (NOTE: you can dismiss this message to cancel sending any announcement)",
                       view=zYesNoButtonView(send_confirmed_race_announcement, (race, msg_text)))

#################################################################################################################
async def pin_race_info(channel_id, race, interaction):
    # Get the channel
    server = get_server_from_interaction(interaction)
    channel = server.get_channel(channel_id)

    if channel is None:
        logging.info(f"Could not find channel with id {channel_id}")
        return False
    
    msg = await post_race_info_message(race, channel)
    db_msg = AsyncRaceMessage(
        server_id=interaction.guild_id,
        channel_id=channel_id,
        message_id=msg.id,
        race_id=race.id,
        message_type=RaceMessageType.RaceInfo)
    try:
        db_msg.save()
    except:
        logging.info("Failed to save race info message to DB in `pin_race_info`")
    return True

####################################################################################################################
async def post_race_info_message(race, channel, for_category=False):
    seed_embed = get_race_info_message(race)
    zRaceInfoButtonView.add_static_embed_fields(seed_embed)
    msg = await channel.send("", view=zRaceInfoButtonView(race.id), embed=seed_embed)
    category_id = None
    if for_category:
        category_id = race.category_id.id
    save_message(race.server_id, channel.id, msg.id, category_id=category_id, message_type=RaceMessageType.RaceInfo)
    return msg

####################################################################################################################
async def remove_category_race_info_messages(interaction, race):
    # Find and remove any existing race info that's pinned for the category
    channel_id = None
    db_msg_list = get_category_race_info_messages(race)
    for m in db_msg_list:
        if m.message_id is not None:
            if channel_id is None: 
                channel_id = m.channel_id
            await delete_message(get_server_from_interaction(interaction), m.id)
    return channel_id

####################################################################################################################
async def pin_race_for_category(interaction, race):
    if race.category_id.pin_recent_race:
        # Find and remove any existing race info that's pinned for the category
        channel_id = await remove_category_race_info_messages(interaction, race)

        # Try to get the channel the previous message was posted in and use that
        channel = None
        if channel_id is not None:
            channel = interaction.guild.get_channel(channel_id)

        # If we still don't have a channel, prompt for one
        if channel is None:
            # Prompt for the channel to pin the race info to
            channel = await prompt_for_channel(interaction, "Choose Channel for Pinned Race Info..")

        # Pin the race info to the channel
        await post_race_info_message(race, channel, for_category=True)

        await send_message(interaction, "Done!")

########################################################################################################################
def get_emoji_list():
    ret_list = copy.copy(EmojiList)
    random.shuffle(ret_list)
    return ret_list

########################################################################################################################
def get_random_emoji():
    return random.choice(EmojiList)

########################################################################################################################
async def show_completed_category_races(interaction, category):
    # Get the list of completed races
    races = get_completed_races_by_category(interaction.user.id, interaction.guild_id)

    if races is None or len(races) == 0:
        await send_message(interaction, "No completed races found.")
        return
    
    # Display it as a paginated list
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id),
                                        style=ButtonStyle.secondary,
                                        timeout=None)
    
    await race_list_menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def show_category_info(interaction, category_id):
    category = get_category(category_id)
    if category is None:
        await send_message(interaction, f"**ERROR** Fetching category with ID {category_id}. Please contact a bot admin.")
        return

    # Get some stats about the category and user
    races = get_completed_races_by_category(category_id)
    num_races = len(races)

    embed = None
    if num_races > 0:
        num_submissions = 0
        num_user_races = 0
        fastest_user_time = ForfeitFinishTimeSeconds
        fastest_user_submission = None
        racers = {}
        fastest_time = ForfeitFinishTimeSeconds
        fastest_submission = None
        for r in races:
            # Get the submissions
            submissions = get_sorted_race_submissions(r.id)
            # Trim off DNFs
            if submissions is not None:
                submissions = list(filter(lambda x: x.finish_time is not ForfeitFinishTime, submissions))
                num_submissions += len(submissions)
                for s in submissions:
                    time_in_seconds = finish_time_to_seconds(s.finish_time)
                    if s.user_id == interaction.user.id:
                        num_user_races += 1
                        if time_in_seconds < fastest_user_time:
                            fastest_user_time = time_in_seconds
                            fastest_user_submission = s

                    if time_in_seconds < fastest_time:
                        fastest_time = time_in_seconds
                        fastest_submission = s

                    if s.user_id not in racers:
                        racers[s.user_id] = 1
                    else:
                        racers[s.user_id] += 1
            else:
                logging.info(f"No submissions found for race {r.id}")
        
        # Create an embed with the category stats
        user = await get_user_from_interaction(interaction, interaction.user.id)
        user_name = get_user_name_str(interaction.user.id, user)
    
        embed = nextcord.Embed(title=f"{category.name} Info", description=f"Stats for {category.name}\n\n{category.description}", color=nextcord.Color.random())
        embed.add_field(name="Total Races", value=num_races, inline=True)
        embed.add_field(name=f"Races by {user_name}", value=num_user_races, inline=True)
        embed.add_field(name="Total Category Submissions", value=num_submissions, inline=True)
        embed.add_field(name="Unique Racers", value=len(racers), inline=True)
        fastest_racer = await get_user_from_interaction(interaction, fastest_submission.user_id)
        fastest_racer_name = get_user_name_str(fastest_submission.user_id, fastest_racer)
        fastest_race = get_race(fastest_submission.race_id)
        fastest_race_name = fastest_race.description if fastest_race is not None else "Unknown Mode"
        embed.add_field(name="Fastest Time",
                        value=f"{fastest_submission.finish_time} by {fastest_racer_name} in {fastest_race_name}",
                        inline=True)
        
        fastest_user_race = get_race(fastest_user_submission.race_id)
        fastest_user_race_name = fastest_user_race.description if fastest_user_race is not None else "Unknown Mode"
        embed.add_field(name=f"{user_name}'s Fastest Time",
                        value=f"{fastest_user_submission.finish_time} by {user_name} in {fastest_user_race_name}",
                        inline=True)
    else:
        # If there are no races yet, just create a basic embed with the category description
        embed = nextcord.Embed(title=f"{category.name} Info", description=f"{category.description}", color=nextcord.Color.random())

    zCategoryInfoButtonView.add_static_embed_fields(embed)
                
    # Create button view to show completed races and leaderboard (if applicable)
    await send_message(interaction, view=zCategoryInfoButtonView(category.id), embed=embed)

########################################################################################################################
async def handle_activate_race(interaction, race):
    # Handle sending the race announcement message (only for open races)
    if not is_assigned_race(race.id):
        await send_race_announcement(interaction, race)

    # Remove the category role from all racers
    if race.category_id.submit_role is not None:
        role = interaction.guild.get_role(race.category_id.submit_role)
        await remove_role_from_members(interaction.guild, role)

        # Sometimes the role removal fails, check the list of members and if any still have the role, try again
        for m in interaction.guild.members:
            if role in m.roles:
                await remove_role_from_members(interaction.guild, role)

    # Pin the race if the category specifies it
    await pin_race_for_category(interaction, race)

    # And update the category leaderboard
    await update_category_leaderboard(interaction, race)

########################################################################################################################
async def do_post_submit_actions(interaction, race, user_id):
    if race is None:
        logging.info(f"**ERROR** Invalid race sent to 'do_post_submit_actions'")
        return
    
    # Apply the submit role if the category or race specifies one
    if race.category_id.submit_role is not None:
        user = await get_user_from_interaction(interaction, user_id)
        if user is not None:
            cat_role = interaction.guild.get_role(race.category_id.submit_role)
            if cat_role is not None:
                await user.add_roles(cat_role)
            race_role = interaction.guild.get_role(race.submission_role)
            if race_role is not None:
                await user.add_roles(race_role)

    # And update the leaderboard
    await update_race_leaderboard(interaction, race)

########################################################################################################################
# Menu Static Data
########################################################################################################################
ModeratorMenuItems = [
    MenuItem(CategoryEmoji , create_edit_category_command, 'create_edit_category'  , 'Categories'          , CreateEditCategoryDescription),
    MenuItem(RaceEmoji     , create_edit_race_command    , 'create_edit_race'      , 'Races'               , CreateEditRaceDescription),
    MenuItem(ExtraInfoEmoji, create_edit_extra_info      , 'create_edit_extra_info', 'Extra Info'          , CreateEditExtraInfoDescription),
    MenuItem(HelpEmoji     , mod_menu_help               , 'mod_menu_help'         , 'Race Moderation Help', RaceModerationHelpDescription),
]

CategoryButtonMenuItems = [
    MenuItem(EditEmoji       , category_edit_description        , 'category_edit_description'        , 'Edit Description'         , CategoryEditDescription),
    MenuItem(DeleteEmoji     , category_delete                  , 'category_delete'                  , 'Delete Category'          , CategoryDeleteDescription),
    MenuItem(EditScoreEmoji  , category_edit_scoring            , 'category_edit_scoring'            , 'Edit Scoring Method'      , CategoryEditScoringDescription),
    MenuItem(SubmitRoleEmoji , category_edit_submit_role        , 'category_edit_submit_role'        , 'Choose Submit Role'       , CategoryEditSubmitRoleDescription),
    MenuItem(CreateRoleEmoji , category_edit_create_role        , 'category_edit_create_role'        , 'Choose Create Ping Role'  , CategoryEditCreateRoleDescription),
    MenuItem(LeaderboardEmoji, category_edit_leaderboard_channel, 'category_edit_leaderboard_channel', 'Set Leaderboard Channel'  , CategorySetLeaderboardChannelDescription),
    MenuItem(EditPointsEmoji , category_edit_points             , 'category_edit_points'             , 'Modify Racer Point Totals', CategoryEditPointsDescription),
    MenuItem(ExtraInfoEmoji  , category_assign_extra_info       , 'category_assign_extra_info'       , 'Assign Submission Value'  , CategoryAssignExtraInfoDescription),
    MenuItem(StatsEmoji      , category_display_raw_submit_info , 'category_display_raw_submit_info' , 'Display Raw Submit Info'  , CategoryDisplayRawSubmitInfoDescription),
    MenuItem(ThumbnailEmoji  , category_set_thumbnail           , 'category_set_thumbnail'           , 'Set Category Thumbnail'   , CategorySetThumbnailDescription),
    MenuItem(ToggleEmoji     , category_misc_toggles            , 'category_misc_toggles'            , 'Misc Category Config'     , CategoryMiscToggleDescription),
]

RaceButtonMenuItems = [
    MenuItem(EditEmoji          , race_edit_core               , 'race_edit_core'               , 'Edit Race'                , RaceEditDescription),
    MenuItem(DeleteEmoji        , race_delete                  , 'race_delete'                  , 'Delete Race'              , RaceDeleteDescription),
    MenuItem(ChangeStateEmoji   , race_change_state            , 'race_change_state'            , 'Change Race State'        , RaceChangeStateDescription),
    MenuItem(PinEmoji           , race_pin                     , 'race_pin'                     , 'Pin Race Info'            , RacePinDescription),
    MenuItem(SubmitRoleEmoji    , race_edit_submit_role        , 'race_edit_submit_role'        , 'Choose Submit Role'       , RaceEditSubmitRoleDescription),
    MenuItem(LeaderboardEmoji   , race_edit_leaderboard_channel, 'race_edit_leaderboard_channel', 'Set Leaderboard Channel'  , RaceEditLeaderboardChannelDescription),
    MenuItem(ExtraInfoEmoji     , race_assign_extra_info       , 'race_assign_extra_info'       , 'Assign Submission Values' , RaceAssignExtraInfoDescription),
    MenuItem(AssignEmoji        , race_assign_racer            , 'race_assign_racer'            , 'Assign Racers'            , RaceAssignRacerDescription),
    MenuItem(EditSubmissionEmoji, race_edit_submission         , 'race_edit_submission'         , 'Modify Submission'        , RaceEditSubmissionDescription),
    #MenuItem(CalendarEmoji      , race_schedule_op             , 'race_schedule_op'             , 'Schedule Operation'       , RaceScheduleOpDescription),
    MenuItem(ToggleEmoji        , race_misc_toggles            , 'race_misc_toggles'            , 'Misc Race Config'         , RaceMiscToggleDescription),
]

RaceModerationHelpMenuItems = [
    MenuItem(CategoryEmoji  , show_category_help        , 'show_category_help'        , 'Category Moderation Help', CategoryHelpDescription),
    MenuItem(EditPointsEmoji, show_category_scoring_help, 'show_category_scoring_help', 'Category Scoring Help'   , CategoryScoringHelpDescription),
    MenuItem(RaceEmoji      , show_race_help            , 'show_race_help'            , 'Race Moderation Help'    , RaceHelpDescription),
    MenuItem(ExtraInfoEmoji , show_extra_info_help      , 'show_extra_info_help'      , 'Extra Info Help'         , ExtraInfoHelpDescription),
]

RacerInfoButtonMenuItems = [
    MenuItem(OpenRacesEmoji     , racer_info_show_open_races     , 'racer_info_show_open_races'     , 'Show Open Races'     , RacerOpenRacesDescription),
    MenuItem(AssignEmoji        , racer_info_show_assigned_races , 'racer_info_show_assigned_races' , 'Show Assigned Races' , RacerAssignedRacesDescription),
    MenuItem(CompletedRacesEmoji, racer_info_show_completed_races, 'racer_info_show_completed_races', 'Show Completed Races', RacerShowCompletedRacesDescription),
    MenuItem(CategoryEmoji      , racer_info_show_categories     , 'racer_info_show_categories'     , 'Show Categories'     , RacerShowCategoriesDescription),
    MenuItem(StatsEmoji         , racer_info_stats               , 'racer_info_stats'               , 'View My Stats'       , RacerStatsDescription),
    MenuItem(EyesEmoji          , racer_info_view_other_racer    , 'racer_info_view_other_racer'    , 'View Another Racer'  , RacerViewOtherRacerDescription),
    MenuItem(HelpEmoji          , show_racer_info_help           , 'show_racer_info_help'           , 'Racer Command Help'  , RacerHelpDescription),
]