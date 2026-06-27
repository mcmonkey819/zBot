# -*- coding: utf-8 -*-
import asyncio
import copy
from datetime import datetime, date, timedelta
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

    @nextcord.ui.button(emoji=PartialEmoji.from_str(ConfirmEmoji))
    async def on_confirm(self, button, interaction):
        self.result = True
        self.stop()

    @nextcord.ui.button(emoji=PartialEmoji.from_str(CrossMarkEmoji))
    async def on_cancel(self, button, interaction):
        self.result = False
        self.stop()

    async def prompt(self, interaction: nextcord.Interaction):
        await menus.Menu.start(self, interaction=interaction, wait=True)
        return self.result
    
########################################################################################################################
class zConfirmThreeOptionMenu(menus.ButtonMenu):
    def __init__(self, msg: str = "", embed=None):
        super().__init__(timeout=None, clear_buttons_after=True)
        self.msg = msg
        self.embed = embed
        self.result = None

    async def send_initial_message(self, ctx, channel):
        await send_message(self.interaction, self.msg, embed=self.embed, view=self)
        return await self.interaction.original_message()

    @nextcord.ui.button(emoji=PartialEmoji.from_str(ConfirmEmoji))
    async def on_confirm(self, button, interaction):
        self.result = True
        self.stop()

    @nextcord.ui.button(emoji=PartialEmoji.from_str(CrossMarkEmoji))
    async def on_cancel(self, button, interaction):
        self.result = False
        self.stop()

    @nextcord.ui.button(emoji=PartialEmoji.from_str(QuestionEmoji))
    async def on_question(self, button, interaction):
        self.result = None
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
        menu.update_buttons(races)

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
        menu.update_buttons(categories)

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
    def __init__(self, submission_list, server_id, bot_client, *, is_team_race = False, per_page: int=10, title=None, body_text=None) -> None:
        self.server_id = server_id
        self.bot_client = bot_client
        self.title = title
        self.body_text = body_text
        self.is_team_race = is_team_race

        super().__init__(entries=submission_list, per_page=per_page)

    async def format_page(self, menu, submissions):
        if self.is_team_race:
            return get_team_race_leaderboard_embed(self.title, self.body_text, submissions, menu.current_page, self.per_page, self.bot_client)
        else:
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
        self.bot_client = bot_client
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
        race = get_race(self.race_id)
        self.is_team_race = False
        if race is not None and race.is_team_race:
            self.is_team_race = True
            self.team_leaderboard_button = zButton(MenuItem(TrophyEmoji, show_team_leaderboard, "show_team_leaderboard", "Show Team Leaderboard", "View the team leaderboard"), 
                                                   self.race_id,
                                                   style=nextcord.ButtonStyle.grey)

            self.add_item(self.team_leaderboard_button)

    async def check_can_submit(self, interaction):
        race = get_race(self.race_id)
        if race is not None:
            if race.state == RaceState.Inactive:
                await send_message(interaction, "Cannot create a submission, this race is Inactive")
                return False
            if race.state == RaceState.Paused:
                await send_message(interaction, "Submissions for this race are currently paused.")
                return False
            if race.state == RaceState.Completed and not race.category_id.allow_completed_submit:
                await send_message(interaction, "The category for this race does not permit submitting to a completed race.")
                return False
            
            # Check if the user has already submitted, if so they can edit that submission only for 4 hours after the intial submission
            submission = get_race_submission(interaction.user.id, self.race_id)
            if submission is not None and not race.category_id.disable_edit_time_limit:
                ts = datetime.fromisoformat(submission.submit_datetime) if type(submission.submit_datetime) is str else submission.submit_datetime
                delta = datetime.now() - ts
                edit_time_limit = timedelta(minutes=2) if bot_config.TEST_MODE else timedelta(hours=4)
                if delta > edit_time_limit:
                    await send_message(interaction, "It is past the window to edit your submission. Please contact a moderator if you need to make changes.")
                    return False
                
            # If this is an assigned race make sure the user is assigned
            if is_assigned_race(self.race_id):
                roster = get_race_assignment(interaction.user.id, self.race_id)
                if roster is None:
                    await send_message(interaction, "Can't submit: This is an assigned race and you are not assigned to it")
                    return False
            
                auto_forfeit_disabled = race.disable_auto_forfeit or race.category_id.disable_auto_forfeit
                if not auto_forfeit_disabled and roster.seed_time is not None:
                    ts = datetime.fromisoformat(roster.seed_time) if type(roster.seed_time) is str else roster.seed_time
                    delta = datetime.now() - ts
                    submit_time_limit = timedelta(minutes=2) if bot_config.TEST_MODE else timedelta(hours=4)
                    if delta > submit_time_limit:
                        await send_message(interaction, "It is past the allowable window after getting the seed to submit. You have been forfeited from this race.")

                        sub = AsyncRaceSubmission()
                        sub.race_id = self.race_id
                        sub.user_id = interaction.user.id
                        sub.submit_datetime = roster.seed_time
                        sub.finish_time = ForfeitFinishTime
                        sub.save()
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
        if can_view_race_leaderboard(interaction.guild, self.race_id, interaction.user):
            await show_race_leaderboard(interaction, self.race_id)
        else:
            await send_message(interaction, "You must submit a time, forfeit or wait for the race to be completed to view the leaderboard")

    def add_static_embed_fields(embed: nextcord.Embed, is_team_race=False):
        embed.add_field(name=f"{TimeEmoji} - Submit/Edit Time", value="Submit a time for this race or edit an already submitted time.", inline=False)
        embed.add_field(name=f"{ForfeitEmoji} - Forfeit", value="Forfeit from this race. Will submit a max time on your behalf and unlock the leaderboard.", inline=False)
        embed.add_field(name=f"{LeaderboardEmoji} - View Leaderboard", value="View the leaderboard for this race.", inline=False)
        if is_team_race:
            embed.add_field(name=f"{TrophyEmoji} - Show Team Leaderboard", value="View the team leaderboard.", inline=False)

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
        
        
        if self.race.is_team_race:
            # Prompt the user to select their teammate
            teammate = await prompt_for_user(interaction, "Select your teammate")

            # Check if the teammate has already submitted a time, and if so make sure they chose this user as their teammate
            teammate_submission = get_race_submission(teammate.id, self.race.id)
            if teammate_submission is not None and teammate_submission.teammate_id != self.submission.user_id:
                await send_message(interaction, "**ERROR** Teammate has already submitted a time and selected a different teammate, make the correct teammate is selected")
                # If this is a self submission we'll error out, but if it's a moderator edit we'll allow it to proceed in order to be able to untangle messes
                if self.user_id is None:
                    return

            self.submission.teammate_id = teammate.id
        
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
                style=nextcord.TextInputStyle.paragraph,
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
async def category_delete(interaction, payload):
    # The button payload is the ToggleField
    menu = payload[0]
    toggle_field = payload[1]

    # ToggleField payload is the category
    category = toggle_field.payload
    
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
async def category_assign_racer(interaction, category):
    # Get the list of races in this category
    cat_races = get_category_races(category.id)

    # Races can be assigned to if they are inactive or active and either are already assigned races or have no submissions
    available_races = []
    for r in cat_races:
        if r.state == RaceState.Inactive:
            available_races.append(r)
        elif r.state in (RaceState.Active, RaceState.Paused):
            if is_assigned_race(r.id) or not race_has_submissions(r.id):
                available_races.append(r)

    # If there are no available races to assign to, inform the user and return
    if len(available_races) == 0:
        await send_message(interaction, CategoryAssignNoAvailableRacesText)
        return

    # Get the list of users to assign
    user_id_list = await prompt_for_assign_list(interaction)

    # Prompt the user how many races they'd like to assign to (including the "all" option)
    select_list = [nextcord.SelectOption(label="All", value=-1, description="Assign to all available races")]
    for i in range(1, len(available_races) + 1):
        select_list.append(nextcord.SelectOption(label=f"{i}", value=i, description=f"Randomly assign to {i} available races"))
    num_races = await zSingleSelectView(select_list, None, "Choose Number of Races...").prompt(interaction)
    if num_races == -1:
        num_races = len(available_races)

    # For the selected racer or each racer in the role
    for u in user_id_list:
        target_races = available_races.copy()
        # We'll handle randomizing the races by shuffling the list of available races
        random.shuffle(target_races)
        # Assign the racer to the selected races
        num_assigned = 0
        for r in target_races:
            # We can't just loop through `num_races` of the shuffled list because the racer may already be assigned
            # to some of the races. This means in some cases we may not assign to the full number
            did_assign = assign_racer(u, r.id)
            if did_assign:
                num_assigned += 1
                if num_assigned == num_races:
                    break

    await send_message(interaction, "Racers assignment complete")

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
async def category_misc_toggles(interaction, category):
    # Build the list of toggle fields
    toggle_list = []
    toggle_list.append(get_delete_category_field(category))
    toggle_list.append(get_ping_assigned_field(category))
    toggle_list.append(get_remove_category_leaderboard_field(category))
    toggle_list.append(get_leaderboard_type_toggle_field(category))
    toggle_list.append(get_category_active_toggle_field(category))
    toggle_list.append(get_category_pin_recent_toggle_field(category))
    toggle_list.append(get_category_allow_completed_submit_toggle_field(category))
    toggle_list.append(get_category_disable_edit_time_limit_toggle_field(category))
    toggle_list.append(get_category_disable_auto_forfeit_toggle_field(category))
    toggle_list.append(get_category_activate_new_races_toggle_field(category))
    toggle_list.append(get_category_mod_view_leaderboard_toggle_field(category))
    
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
def get_category_disable_edit_time_limit_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_disable_edit_time_limit,
        payload=category,
        button_style=bool_field_button_style(category.disable_edit_time_limit),
        custom_id=toggle_category_disable_edit_time_limit_id,
        emoji=TimeEmoji,
        embed_field=EmbedField(name=f"{TimeEmoji} - Allow Unlimited Submission Edits",
                               value=bool_field_to_str(category.disable_edit_time_limit),
                               inline=False))

########################################################################################################################
def get_category_disable_auto_forfeit_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_disable_auto_forfeit,
        payload=category,
        button_style=bool_field_button_style(category.disable_auto_forfeit),
        custom_id=toggle_category_disable_auto_forfeit_id,
        emoji=TimeEmoji,
        embed_field=EmbedField(name=f"{TimeEmoji} - Disable Auto-Forfeit After Seed View",
                               value=bool_field_to_str(category.disable_auto_forfeit),
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
def get_category_mod_view_leaderboard_toggle_field(category):
    return ToggleField(
        toggle_func=toggle_category_mod_view_leaderboard,
        payload=category,
        button_style=bool_field_button_style(category.mod_can_view_leaderboard),
        custom_id=toggle_category_mod_view_leaderboard_id,
        emoji=EyesEmoji,
        embed_field=EmbedField(name=f"{EyesEmoji} - Mods Can View Leaderboard",
                               value=bool_field_to_str(category.mod_can_view_leaderboard),
                               inline=False))

########################################################################################################################
def get_delete_category_field(category):
    return ToggleField(
        toggle_func=category_delete,
        payload=category,
        button_style=nextcord.ButtonStyle.blurple,
        custom_id='category_delete',
        emoji=DeleteEmoji,
        embed_field=EmbedField(name=f"{DeleteEmoji} - Delete Category",
                               value=CategoryDeleteDescription,
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
        emoji=CrossMarkEmoji,
        embed_field=EmbedField(name=f"{CrossMarkEmoji} - Remove Leaderboard",
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
async def race_delete(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]

    # ToggleField payload is the race
    race = toggle_field.payload

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

    # Enforce Paused transition constraints
    if new_state == RaceState.Paused and race.state != RaceState.Active:
        await send_message(interaction, "A race can only be paused from Active state.")
        return
    if race.state == RaceState.Paused and new_state != RaceState.Active:
        await send_message(interaction, "A paused race can only be set back to Active.")
        return

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
    previous_state = race.state
    race.state = new_state
    race.save()

    if new_state == RaceState.Active:
        if previous_state != RaceState.Paused:
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
    # Races can't be assigned in the completed state
    if race.state == RaceState.Completed:
        await send_message(interaction, "Can't assign racers in the `Complete` state.")
        return
    
    if race.state in (RaceState.Active, RaceState.Paused):
        # Can't assign racers if there are no assigned racers yet and there are submissions
        if race_has_submissions(race.id) and not is_assigned_race(race.id):
            await send_message(interaction, "Can't assign racers because the race is active and there are already submissions as an open race.")
            return
    
    user_id_list = await prompt_for_assign_list(interaction)
    # Create an assignment for each member returned
    for u in user_id_list:
        assign_racer(user_id=u, race_id=race.id)
    await send_message(interaction, "Role assignment complete")
    
########################################################################################################################
async def prompt_for_assign_list(interaction):
    user_id_list = []
    
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
        user_id_list.append(user.id)
    elif assign_type == 2:
        # Prompt for the role to assign
        role_id = await prompt_for_role(interaction)

        if role_id is None:
            await send_message(interaction, "**ERROR** - No role selected, cancelled assignment")
        else:
            role = interaction.guild.get_role(role_id)

            if role is None:
                await send_message(interaction, "**ERROR** - Role not found, cancelled assignment")
            else:
                for m in role.members:
                    user_id_list.append(m.id)
    else:
        await send_message(interaction, "**ERROR** - Unknown option selected, cancelled assignment")
    
    return user_id_list
    
########################################################################################################################
async def race_edit_submission(interaction, race):
    await defer(interaction)
    
    if race.state == RaceState.Inactive:
        await send_message(interaction, "Cannot create submissions for an Inactive race.")
        return
    
    # Get a list of submissions for this race
    submissions = get_sorted_race_submissions(race.id)

    # Create a select list from the submissions
    select_list = [nextcord.SelectOption(label="Create New...", value=-1, description="Create a new submission"),
                   nextcord.SelectOption(label="Cancel...", value=0, description="Cancel the operation")]
    if submissions is not None:
        for s in submissions:
            try:
                user = await get_user_from_interaction(interaction, s.user_id)
                user_name = get_user_name_str(s.user_id, user)
            except:
                user_name = "Unknown"
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
async def race_validate_submission(interaction, race):
    # Get a list of submissions for this race
    submissions = get_sorted_race_submissions(race.id)

    if submissions is not None:
        # Create a select list from the submissions
        select_list = [nextcord.SelectOption(label="Cancel...", value=0, description="Cancel the operation")]
        for s in submissions:
            user = await get_user_from_interaction(interaction, s.user_id)
            user_name = get_user_name_str(s.user_id, user)
            r = get_race_assignment(s.user_id, race.id)
            emoji = QuestionEmoji
            if r is not None:
                if r.validation_status == ValidationStatus.Verified:
                    emoji = ConfirmEmoji
                elif r.validation_status == ValidationStatus.Rejected:
                    emoji = CrossMarkEmoji
            select_list.append(nextcord.SelectOption(label=f"{emoji} {user_name} - {s.finish_time}", value=s.id, description=f"{user_name} - {s.finish_time}"))
    
        # Prompt the user to select a submission
        submission_id = await zSingleSelectView(select_list, None, "Choose Submission To Validate..").prompt(interaction)

        if submission_id == 0:
            await send_message(interaction, "Cancelled")
            return
        
        # Get the submission
        submission = get_race_submission_by_id(submission_id)
        if submission is None:
            await send_message(interaction, f"**ERROR** Submission {submission_id} not found. Contact a bot admin.")
            return
        
        # Get the roster entry (if it exists) to get the seed access time
        roster = get_race_assignment(submission.user_id, race.id)
        seed_access_time = None if roster is None else roster.seed_time

        # Get validation status
        validation_status = roster.validation_status
        
        # Build an embed with the submission info
        server = get_server_from_interaction(interaction)
        user = await server.fetch_member(submission.user_id)
        user_name = get_user_name_str(submission.user_id, user)
        embed = nextcord.Embed(color=nextcord.Colour.random(), title=f"Validate Submission", description=ValidateSubmissionEmbedDescription)
        embed.add_field(name=f"Racer Name", value=user_name, inline=False)
        embed.add_field(name=f"Validation Status", value=get_validation_status_str(validation_status), inline=False)
        embed.add_field(name=f"Seed Access Date/Time", value=seed_access_time, inline=False)
        embed.add_field(name=f"Submit Date/Time", value=submission.submit_datetime, inline=False)
        details = get_submission_details_dict(submission)
        for k, v in details.items():
            embed.add_field(name=k, value=v, inline=False)

        # Send the embed to the user along with some buttons to choose the validation status
        validation_selection = await zConfirmThreeOptionMenu(msg="", embed=embed).prompt(interaction)

        # Update the validation status based on the user selection
        if validation_selection is None:
            validation_status = ValidationStatus.Unverified
        elif validation_selection:
            validation_status = ValidationStatus.Verified
        else:
            validation_status = ValidationStatus.Rejected

        roster.validation_status = validation_status
        roster.save()
        await send_message(interaction, f"Submission marked as {ValidationStatus.to_str(validation_status)}")

    else:
        await send_message(interaction, "No submissions found for this race")
        

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
    toggle_list.append(get_delete_race_field(race))
    toggle_list.append(get_remove_race_leaderboard_field(race))
    toggle_list.append(get_is_team_race_field(race))
    toggle_list.append(get_race_disable_auto_forfeit_field(race))
    
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
def get_delete_race_field(race):
    return ToggleField(
        toggle_func=race_delete,
        payload=race,
        button_style=nextcord.ButtonStyle.blurple,
        custom_id='race_delete' ,
        emoji=DeleteEmoji,
        embed_field=EmbedField(name=f"{DeleteEmoji} - Delete Race",
                               value=RaceDeleteDescription,
                               inline=False))

########################################################################################################################
def get_remove_race_leaderboard_field(race):
    return ToggleField(
        toggle_func=race_remove_channel_leaderboard,
        payload=race,
        button_style=nextcord.ButtonStyle.blurple,
        custom_id=remove_race_leaderboard_id,
        emoji=CrossMarkEmoji,
        embed_field=EmbedField(name=f"{CrossMarkEmoji} - Remove Leaderboard",
                               value="Button will remove any leaderboard channel assignment and delete leaderboard messages.",
                               inline=False))
        
########################################################################################################################
def get_is_team_race_field(race):
    return ToggleField(
        toggle_func=race_toggle_is_team_race,
        payload=race,
        button_style=bool_field_button_style(race.is_team_race),
        custom_id=toggle_is_team_race_id,
        emoji=TrophyEmoji,
        embed_field=EmbedField(name=f"{TrophyEmoji} - Is Team Race",
                               value=bool_field_to_str(race.is_team_race),
                               inline=False))

########################################################################################################################
def get_race_disable_auto_forfeit_field(race):
    return ToggleField(
        toggle_func=race_toggle_disable_auto_forfeit,
        payload=race,
        button_style=bool_field_button_style(race.disable_auto_forfeit),
        custom_id=toggle_race_disable_auto_forfeit_id,
        emoji=TimeEmoji,
        embed_field=EmbedField(name=f"{TimeEmoji} - Disable Auto-Forfeit After Seed View",
                               value=bool_field_to_str(race.disable_auto_forfeit),
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
    user_name = get_user_name_str(interaction.user.id, interaction.user)
    race_id_list = [r.id for r in races]
    logging.info(f"User {user_name} used show assigned, got race list {race_id_list}")

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
async def prompt_for_user(interaction, placeholder="Choose User..."):
    selected_user = await zUserSelectView(None, placeholder=placeholder).prompt(interaction)
    return selected_user

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
    zRaceInfoButtonView.add_static_embed_fields(seed_embed, race.is_team_race)
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
async def post_channel_race_leaderboard(interaction, channel, race_id, bot_client, emojis, save_as_category_message=False, server_id=None):
    per_page=10
    submissions = get_sorted_race_submissions(race_id)
    effective_server_id = server_id if server_id is not None else interaction.guild_id

    title = get_race_leaderboard_title(race_id)
    body_text = get_race_leaderboard_description(race_id)
    race = get_race(race_id)

    if len(submissions) == 0:
        msg_text = f"**{title}**\n\n{body_text}\n\nNo submissions yet"
        msg = await channel.send(msg_text)
        if save_as_category_message:
            save_message(effective_server_id, channel.id, msg.id, category_id=race.category_id.id)
        else:
            save_message(effective_server_id, channel.id, msg.id, race_id=race_id)
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
            save_message(effective_server_id, channel.id, msg.id, category_id=race.category_id.id)
        else:
            logging.info(f"Saving race leaderboard {race_id} as a race message")
            save_message(effective_server_id, channel.id, msg.id, race_id=race_id)

########################################################################################################################
async def show_team_leaderboard(interaction, race_id):
    submissions = get_sorted_race_submissions(race_id)
    race = get_race(race_id)

    sub_ids = {}
    team_submissions = []
    for s in submissions:
        # If we've already handlled this submission, skip it
        if s.id in sub_ids:
            continue

        # Find the matching submission from teammate
        teammate_submission = None
        sub_ids[s.id] = True
        if s.teammate_id is not None:
            for t in submissions:
                if t.id not in sub_ids and t.user_id == s.teammate_id:
                    teammate_submission = t
                    if teammate_submission.teammate_id != s.user_id:
                        logging.info(f"**ERROR** Teammate ID mismatch for submission {s.id}")
                        teammate_submission = None
                    else:
                        sub_ids[t.id] = True
                    break
                
        # Get the team name, if it exists. Faster teammate gets to pick the team name
        team_name = get_extra_info(s.id, race.team_name_info_id)
        team_name_str = None
        if team_name is None and teammate_submission is not None:
            # But if the faster teammate doesn't specify a team name, check the teammate's submission for a valid name
            team_name = get_extra_info(teammate_submission.id, race.team_name_info_id)
            
        if team_name is not None:
            team_name_str = team_name.data
            

        total_finish_time_sec = 0
        # Get the username strings
        user_names = []
        user_names.append(get_user_name_str(s.user_id, interaction.guild.get_member(s.user_id)))
        if teammate_submission is not None:
            user_names.append(get_user_name_str(teammate_submission.user_id, interaction.guild.get_member(teammate_submission.user_id)))
        # If we still don't have a team name, just combine the usernames
        if team_name_str is None:
            logging.info(f"**ERROR** Team name not found for submission {s.id}")
            team_name_str = f"Team {user_names[0]}"
            if teammate_submission is not None:
                team_name_str += f" & {user_names[1]}"
        # Calculate the average finish time
        if teammate_submission is not None:
            total_finish_time_sec = finish_time_to_seconds(s.finish_time) + finish_time_to_seconds(teammate_submission.finish_time)
            avg_finish_time_sec = int(total_finish_time_sec / 2)
        else:
            avg_finish_time_sec = finish_time_to_seconds(s.finish_time)

        logging.info(f"Team: {team_name_str}, Avg Finish Time Seconds: {avg_finish_time_sec}")
        avg_finish_time = finish_time_seconds_to_str(avg_finish_time_sec) 
        
        # Finally construct and add the team submission data object
        team_submissions.append(TeamSubmissionData(team_name_str, user_names, avg_finish_time, [s.finish_time, teammate_submission.finish_time if teammate_submission is not None else None]))

    # Sort the list by finish time
    team_submissions.sort(key=lambda x: finish_time_to_seconds(x.team_finish_time))
    
    # Finally show the team leaderboard menu
    menu = zRaceLeaderboardMenuPages(source=zRaceLeaderboardPageSource(team_submissions, 
                                                                       interaction.guild_id,
                                                                       interaction.client,
                                                                       title=get_race_leaderboard_title(race_id),
                                                                       body_text=get_race_leaderboard_description(race_id),
                                                                       is_team_race=True))
    await menu.start(interaction=interaction, ephemeral=True)

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
async def post_channel_category_leaderboard(interaction, channel, category_id, bot_client, server_id=None):
    per_page = 8
    effective_server_id = server_id if server_id is not None else interaction.guild_id
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
            await post_channel_race_leaderboard(interaction, channel, race.id, bot_client, get_emoji_list(),
                                                save_as_category_message=True, server_id=effective_server_id)
    else:
        embed_list = await get_category_leaderboard_embed_list(category_id, per_page, bot_client)
        if embed_list is None or len(embed_list) == 0:
            msg = await channel.send(f"No points scored yet for category {category.name}. This is likely due to no completed races.")
            save_message(effective_server_id, channel.id, msg.id, category_id=category_id)
        else:
            for e in embed_list:
                msg = await channel.send(embed=e)
                save_message(effective_server_id, channel.id, msg.id, category_id=category_id)

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
async def race_toggle_is_team_race(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]
    
    # ToggleField payload is the race
    race = toggle_field.payload

    race.is_team_race = not race.is_team_race
    select_list = []
    if race.is_team_race:
        # If the race is being toggled to a team race, prompt for the extra info type to use for team names
        extra_infos = get_race_extra_info_assignments(race.id)
        for a in extra_infos:
            select_list.append(nextcord.SelectOption(label=a.info_type_id.name, value=a.info_type_id.id, description=a.info_type_id.description))

        if len(select_list) == 0:
            await send_message(interaction, "No extra info types assigned to this race, you must assign an extra info type to use for team names first.")
            race.is_team_race = False
    race.save()

    # Update the button style
    toggle_field.button_style = bool_field_button_style(race.is_team_race)

    # Update the embed field value
    toggle_field.embed_field.value = bool_field_to_str(race.is_team_race)

    # Update the menu
    await update_menu_embed_field(menu, toggle_field)

    # If we've just set this as a team race, prompt for the extra info type to use for team names
    if race.is_team_race:
        team_name_info_id = await zSingleSelectView(select_list, None, "Select Team Name Field").prompt(interaction)
        if team_name_info_id is not None:
            race.team_name_info_id = team_name_info_id
            race.save()
            await send_message(interaction, f"Team Name Field {get_extra_info_type(team_name_info_id).name} saved")
                                                 
########################################################################################################################
async def race_toggle_disable_auto_forfeit(interaction, payload):
    menu = payload[0]
    toggle_field = payload[1]
    race = toggle_field.payload
    race.disable_auto_forfeit = not race.disable_auto_forfeit
    race.save()
    toggle_field.button_style = bool_field_button_style(race.disable_auto_forfeit)
    toggle_field.embed_field.value = bool_field_to_str(race.disable_auto_forfeit)
    await update_menu_embed_field(menu, toggle_field)

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
async def toggle_category_disable_edit_time_limit(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]

    # ToggleField payload is the category
    category = toggle_field.payload

    category.disable_edit_time_limit = not category.disable_edit_time_limit
    category.save()

    # Then update the button style
    toggle_field.button_style = bool_field_button_style(category.disable_edit_time_limit)

    # Then update the embed field value
    toggle_field.embed_field.value = bool_field_to_str(category.disable_edit_time_limit)

    # Finally update the menu
    await update_menu_embed_field(menu, toggle_field)

########################################################################################################################
async def toggle_category_disable_auto_forfeit(interaction, payload):
    menu = payload[0]
    toggle_field = payload[1]
    category = toggle_field.payload
    category.disable_auto_forfeit = not category.disable_auto_forfeit
    category.save()
    toggle_field.button_style = bool_field_button_style(category.disable_auto_forfeit)
    toggle_field.embed_field.value = bool_field_to_str(category.disable_auto_forfeit)
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
async def toggle_category_mod_view_leaderboard(interaction, payload):
    # The button payload is a tuple with the menu and ToggleField
    menu = payload[0]
    toggle_field = payload[1]
    
    # ToggleField payload is the category
    category = toggle_field.payload

    category.mod_can_view_leaderboard = not category.mod_can_view_leaderboard
    category.save()

    # Then update the button style
    toggle_field.button_style = bool_field_button_style(category.mod_can_view_leaderboard)

    # Then update the embed field value
    toggle_field.embed_field.value = bool_field_to_str(category.mod_can_view_leaderboard)

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
    
    await post_race_info_message(race, channel)
    return True

####################################################################################################################
async def post_race_info_message(race, channel, for_category=False):
    seed_embed = get_race_info_message(race)
    zRaceInfoButtonView.add_static_embed_fields(seed_embed, race.is_team_race)
    msg = await channel.send("", view=zRaceInfoButtonView(race.id), embed=seed_embed)
    category_id = None
    if for_category:
        category_id = race.category_id.id
    save_message(race.server_id, channel.id, msg.id, race_id=race.id, category_id=category_id, message_type=RaceMessageType.RaceInfo)
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
        
        if fastest_user_submission is not None:
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
def get_validation_status_str(validation_status):
    ## CMC TODO ##
    return f"{QuestionEmoji} Unverified"

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
    MenuItem(EditScoreEmoji  , category_edit_scoring            , 'category_edit_scoring'            , 'Edit Scoring Method'      , CategoryEditScoringDescription),
    MenuItem(SubmitRoleEmoji , category_edit_submit_role        , 'category_edit_submit_role'        , 'Choose Submit Role'       , CategoryEditSubmitRoleDescription),
    MenuItem(CreateRoleEmoji , category_edit_create_role        , 'category_edit_create_role'        , 'Choose Create Ping Role'  , CategoryEditCreateRoleDescription),
    MenuItem(LeaderboardEmoji, category_edit_leaderboard_channel, 'category_edit_leaderboard_channel', 'Set Leaderboard Channel'  , CategorySetLeaderboardChannelDescription),
    MenuItem(EditPointsEmoji , category_edit_points             , 'category_edit_points'             , 'Modify Racer Point Totals', CategoryEditPointsDescription),
    MenuItem(AssignEmoji     , category_assign_racer            , 'category_assign_racer'            , 'Assign Racers'            , CategoryAssignRacerDescription),
    MenuItem(ExtraInfoEmoji  , category_assign_extra_info       , 'category_assign_extra_info'       , 'Assign Submission Value'  , CategoryAssignExtraInfoDescription),
    MenuItem(StatsEmoji      , category_display_raw_submit_info , 'category_display_raw_submit_info' , 'Display Raw Submit Info'  , CategoryDisplayRawSubmitInfoDescription),
    MenuItem(ThumbnailEmoji  , category_set_thumbnail           , 'category_set_thumbnail'           , 'Set Category Thumbnail'   , CategorySetThumbnailDescription),
    MenuItem(ToggleEmoji     , category_misc_toggles            , 'category_misc_toggles'            , 'Misc Category Config'     , CategoryMiscToggleDescription),
]

RaceButtonMenuItems = [
    MenuItem(EditEmoji          , race_edit_core               , 'race_edit_core'               , 'Edit Race'                , RaceEditDescription),
    MenuItem(ChangeStateEmoji   , race_change_state            , 'race_change_state'            , 'Change Race State'        , RaceChangeStateDescription),
    MenuItem(PinEmoji           , race_pin                     , 'race_pin'                     , 'Pin Race Info'            , RacePinDescription),
    MenuItem(SubmitRoleEmoji    , race_edit_submit_role        , 'race_edit_submit_role'        , 'Choose Submit Role'       , RaceEditSubmitRoleDescription),
    MenuItem(LeaderboardEmoji   , race_edit_leaderboard_channel, 'race_edit_leaderboard_channel', 'Set Leaderboard Channel'  , RaceEditLeaderboardChannelDescription),
    MenuItem(ExtraInfoEmoji     , race_assign_extra_info       , 'race_assign_extra_info'       , 'Assign Submission Values' , RaceAssignExtraInfoDescription),
    MenuItem(AssignEmoji        , race_assign_racer            , 'race_assign_racer'            , 'Assign Racers'            , RaceAssignRacerDescription),
    MenuItem(EditSubmissionEmoji, race_edit_submission         , 'race_edit_submission'         , 'Modify Submission'        , RaceEditSubmissionDescription),
    MenuItem(EditScoreEmoji     , race_validate_submission     , 'race_validate_submission'     , 'Validate Submission'      , RaceValidateSubmissionDescription),
    #MenuItem(CalendarEmoji      , race_schedule_op             , 'race_schedule_op'             , 'Schedule Operation'       , RaceScheduleOpDescription),
    MenuItem(ToggleEmoji         , race_misc_toggles            , 'race_misc_toggles'            , 'Misc Race Config'         , RaceMiscToggleDescription),
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

########################################################################################################################
class ServerConfigView(nextcord.ui.View):
    """Ephemeral view for /async_admin server_config. Lets admins update server-level settings."""

    def __init__(self, db_server, discord_server, original_interaction):
        super().__init__(timeout=300)
        self.db_server = db_server
        self.discord_server = discord_server
        self.original_interaction = original_interaction
        # Initialise toggle button labels/styles to reflect current DB state
        self.toggle_vc.label = f"VC Creation: {'ON' if db_server.enable_vc_create else 'OFF'}"
        self.toggle_vc.style = nextcord.ButtonStyle.green if db_server.enable_vc_create else nextcord.ButtonStyle.grey
        self.toggle_trials.label = f"Trials: {'Enabled' if db_server.trials_enabled else 'Disabled'}"
        self.toggle_trials.style = nextcord.ButtonStyle.green if db_server.trials_enabled else nextcord.ButtonStyle.grey

    def build_embed(self):
        embed = nextcord.Embed(title="Server Configuration", color=nextcord.Colour.blurple())

        if self.db_server.admin_role_id:
            role = self.discord_server.get_role(self.db_server.admin_role_id)
            embed.add_field(name="Admin Role",
                            value=f"✅ {role.name}" if role else f"✅ ID {self.db_server.admin_role_id} (not found)",
                            inline=True)
        else:
            embed.add_field(name="Admin Role", value="❌ Not set", inline=True)

        if self.db_server.mod_role_id:
            role = self.discord_server.get_role(self.db_server.mod_role_id)
            embed.add_field(name="Mod Role",
                            value=f"✅ {role.name}" if role else f"✅ ID {self.db_server.mod_role_id} (not found)",
                            inline=True)
        else:
            embed.add_field(name="Mod Role", value="❌ Not set", inline=True)

        embed.add_field(name="VC Creation",
                        value="✅ Enabled" if self.db_server.enable_vc_create else "❌ Disabled",
                        inline=True)
        embed.add_field(name="Trials",
                        value="✅ Enabled" if self.db_server.trials_enabled else "❌ Disabled",
                        inline=True)

        if self.db_server.trials_enabled:
            if self.db_server.trials_announcement_channel_id:
                ch = self.discord_server.get_channel(self.db_server.trials_announcement_channel_id)
                ch_val = f"✅ #{ch.name}" if ch else f"✅ ID {self.db_server.trials_announcement_channel_id} (not found)"
            else:
                ch_val = "❌ Not set"
            embed.add_field(name="Trial Announcements Channel", value=ch_val, inline=True)

            if self.db_server.trials_discord_category_id:
                cat = self.discord_server.get_channel(self.db_server.trials_discord_category_id)
                cat_val = f"✅ {cat.name}" if cat else f"✅ ID {self.db_server.trials_discord_category_id} (not found)"
            else:
                cat_val = "❌ Not set"
            embed.add_field(name="Trials Channel Category", value=cat_val, inline=True)

        return embed

    async def _refresh(self):
        await self.original_interaction.edit_original_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        try:
            await self.original_interaction.edit_original_message(view=None)
        except Exception:
            pass

    @nextcord.ui.button(label="Set Admin Role", style=nextcord.ButtonStyle.blurple, row=0)
    async def set_admin_role(self, button, interaction):
        role_list = get_role_select_list(self.discord_server)
        view = zSingleSelectView(role_list, None, "Select Admin Role...")
        await interaction.response.send_message("Select the admin role:", view=view, ephemeral=True)
        await view.wait()
        role_id = view.get_selected_value()
        if role_id is not None and role_id != 0:
            self.db_server.admin_role_id = role_id
            self.db_server.save()
        await self._refresh()

    @nextcord.ui.button(label="Set Mod Role", style=nextcord.ButtonStyle.blurple, row=0)
    async def set_mod_role(self, button, interaction):
        role_list = get_role_select_list(self.discord_server)
        view = zSingleSelectView(role_list, None, "Select Mod Role...")
        await interaction.response.send_message("Select the mod role:", view=view, ephemeral=True)
        await view.wait()
        role_id = view.get_selected_value()
        if role_id is not None and role_id != 0:
            self.db_server.mod_role_id = role_id
            self.db_server.save()
        await self._refresh()

    @nextcord.ui.button(label="VC Creation: OFF", style=nextcord.ButtonStyle.grey, row=1)
    async def toggle_vc(self, button, interaction):
        self.db_server.enable_vc_create = not self.db_server.enable_vc_create
        self.db_server.save()
        button.label = f"VC Creation: {'ON' if self.db_server.enable_vc_create else 'OFF'}"
        button.style = nextcord.ButtonStyle.green if self.db_server.enable_vc_create else nextcord.ButtonStyle.grey
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @nextcord.ui.button(label="Trials: Disabled", style=nextcord.ButtonStyle.grey, row=1)
    async def toggle_trials(self, button, interaction):
        self.db_server.trials_enabled = not self.db_server.trials_enabled
        self.db_server.save()
        button.label = f"Trials: {'Enabled' if self.db_server.trials_enabled else 'Disabled'}"
        button.style = nextcord.ButtonStyle.green if self.db_server.trials_enabled else nextcord.ButtonStyle.grey
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @nextcord.ui.button(label="Set Announcement Channel", style=nextcord.ButtonStyle.blurple, row=2)
    async def set_announcement_channel(self, button, interaction):
        if not self.db_server.trials_enabled:
            await interaction.response.send_message("Enable Trials first.", ephemeral=True)
            return
        channel_list = await get_permitted_channel_select_list(interaction.client.user.id, self.discord_server)
        view = zSingleSelectView(channel_list, None, "Select Announcement Channel...")
        await interaction.response.send_message("Select the trial announcements channel:", view=view, ephemeral=True)
        await view.wait()
        channel_id = view.get_selected_value()
        if channel_id is not None and channel_id != 0:
            self.db_server.trials_announcement_channel_id = channel_id
            self.db_server.save()
        await self._refresh()

    @nextcord.ui.button(label="Set Trials Category", style=nextcord.ButtonStyle.blurple, row=2)
    async def set_trials_category(self, button, interaction):
        if not self.db_server.trials_enabled:
            await interaction.response.send_message("Enable Trials first.", ephemeral=True)
            return
        cat_list = [nextcord.SelectOption(label=c.name, value=c.id, description=c.name)
                    for c in self.discord_server.categories]
        if not cat_list:
            await interaction.response.send_message("No Discord channel categories found in this server.", ephemeral=True)
            return
        view = zSingleSelectView(cat_list, None, "Select Trials Channel Category...")
        await interaction.response.send_message("Select the Discord category for trial channels:", view=view, ephemeral=True)
        await view.wait()
        cat_id = view.get_selected_value()
        if cat_id is not None:
            self.db_server.trials_discord_category_id = cat_id
            self.db_server.save()
        await self._refresh()

    @nextcord.ui.button(label="Done", style=nextcord.ButtonStyle.green, row=4)
    async def done(self, button, interaction):
        await interaction.response.edit_message(view=None)
        self.stop()

########################################################################################################################
# TRIAL ANNOUNCEMENT FLOW
########################################################################################################################

########################################################################################################################
class TrialDetailsModal(zModal):
    """Single modal: trial name, description, optional announcement text, and min signups."""

    def __init__(self, has_text, submit_handler):
        fields = {
            'name': nextcord.ui.TextInput(
                label="Trial Name",
                required=True,
                custom_id='name',
                placeholder="Used for role names, category name, and display",
                row=1),
            'short_description': nextcord.ui.TextInput(
                label="Short Description",
                required=False,
                custom_id='short_description',
                placeholder="Bot category description (~100 chars)",
                row=2),
            'min_signups': nextcord.ui.TextInput(
                label="Minimum Signups to Notify Organizer",
                required=False,
                custom_id='min_signups',
                placeholder="Leave blank to disable",
                row=3),
        }
        if has_text:
            fields['announcement_text'] = nextcord.ui.TextInput(
                label="Announcement Text",
                required=True,
                custom_id='announcement_text',
                style=nextcord.TextInputStyle.paragraph,
                row=4)
        super().__init__(fields, submit_handler, "Trial Details")

########################################################################################################################
class TrialOrganizerSelectView(nextcord.ui.View):
    """First step of announce_trial — pick the organizer via UserSelect or skip."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow

    def _open_details_modal(self, interaction):
        return interaction.response.send_modal(
            TrialDetailsModal(
                has_text=(self.flow.existing_message_id is None),
                submit_handler=self.flow._on_details_submit))

    @nextcord.ui.user_select(placeholder="Select trial organizer...")
    async def organizer_select(self, select, interaction):
        self.flow.organizer_user_id = select.values[0].id
        await self._open_details_modal(interaction)
        self.stop()

    @nextcord.ui.button(label="No Organizer", style=nextcord.ButtonStyle.grey, row=1)
    async def skip_button(self, button, interaction):
        self.flow.organizer_user_id = None
        await self._open_details_modal(interaction)
        self.stop()

########################################################################################################################
class TrialRoleNameView(nextcord.ui.View):
    """Shows the proposed participant role name with [Edit Name] and [Create Role] buttons."""

    def __init__(self, flow, proposed_name):
        super().__init__(timeout=300)
        self.flow = flow
        self.current_name = proposed_name

    @nextcord.ui.button(label="Edit Name", style=nextcord.ButtonStyle.blurple)
    async def edit_name(self, button, interaction):
        modal = zModal(
            {'name': nextcord.ui.TextInput(
                label="Role Name",
                default_value=self.current_name,
                required=True,
                custom_id='name',
                row=1)},
            self._on_name_edit,
            "Edit Role Name")
        await interaction.response.send_modal(modal)

    async def _on_name_edit(self, interaction, modal):
        for child in modal.children:
            if child.custom_id == 'name':
                self.current_name = child.value
        new_view = TrialRoleNameView(self.flow, self.current_name)
        await send_message(
            interaction,
            f"Updated role name: **{self.current_name}**\nClick **Edit Name** to change or **Next** to proceed.",
            view=new_view)

    @nextcord.ui.button(label="Next", style=nextcord.ButtonStyle.green)
    async def create_role(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.flow.on_role_name_confirmed(interaction, self.current_name)
        self.stop()

########################################################################################################################
class TrialAnnounceFlow:
    """Manages the multi-step /announce_trial flow across modals and views."""

    def __init__(self, db_server, discord_server, message_id, trial_cache):
        self.db_server = db_server
        self.discord_server = discord_server
        self.existing_message_id = message_id  # int or None
        self.trial_cache = trial_cache
        # Accumulated across modals
        self.name = None
        self.short_description = None
        self.announcement_text = None
        self.organizer_user_id = None
        self.min_signups = None

    async def start(self, interaction):
        view = TrialOrganizerSelectView(self)
        await interaction.response.send_message(
            "Select the trial organizer (receives a DM when the minimum signup threshold is reached):",
            view=view,
            ephemeral=True)

    async def _on_details_submit(self, interaction, modal):
        for child in modal.children:
            match child.custom_id:
                case 'name':              self.name = child.value.strip()
                case 'short_description': self.short_description = child.value.strip()
                case 'announcement_text': self.announcement_text = child.value.strip()
                case 'min_signups':
                    raw = child.value.strip()
                    self.min_signups = int(raw) if raw.isdigit() else None
        view = TrialRoleNameView(self, self.name)
        await send_message(
            interaction,
            f"Proposed participant role name: **{self.name}**\nClick **Edit Name** to change or **Next** to proceed.",
            view=view)

    async def on_role_name_confirmed(self, interaction, role_name):
        # Create participant role
        try:
            role = await self.discord_server.create_role(name=role_name, reason="Trial participant role")
        except Exception as e:
            await send_message(interaction, f"**ERROR** Could not create participant role: {e}")
            return

        # Post announcement message if the bot is posting it
        announcement_message_id = self.existing_message_id
        if announcement_message_id is None:
            channel = self.discord_server.get_channel(self.db_server.trials_announcement_channel_id)
            if channel is None:
                await role.delete(reason="Trial creation failed — announcement channel not found")
                await send_message(interaction, "**ERROR** Announcement channel not found.")
                return
            try:
                msg = await channel.send(self.announcement_text)
                announcement_message_id = msg.id
            except Exception as e:
                await role.delete(reason="Trial creation failed — could not post announcement")
                await send_message(interaction, f"**ERROR** Could not post announcement: {e}")
                return

        # Save Trial record
        trial = Trial()
        trial.server_id = self.db_server.id
        trial.short_name = self.name
        trial.display_name = self.name
        trial.short_description = self.short_description or ''
        trial.announcement_text = self.announcement_text
        trial.state = TrialState.Announcing
        trial.accept_signups = True
        trial.announcement_message_id = announcement_message_id
        trial.announcement_channel_id = self.db_server.trials_announcement_channel_id
        trial.participant_role_id = role.id
        trial.organizer_user_id = self.organizer_user_id
        trial.min_signups = self.min_signups
        try:
            trial.save()
        except Exception as e:
            await role.delete(reason="Trial creation failed — DB error")
            await send_message(interaction, f"**ERROR** Could not save trial: {e}")
            return

        # Add to reaction cache
        self.trial_cache[announcement_message_id] = trial

        if self.existing_message_id is not None:
            await send_message(interaction, f"Attached to existing message. Tracking reactions for **{self.name}** signups.")
        else:
            await send_message(interaction, f"Announcement posted. Tracking reactions for **{self.name}** signups.")

########################################################################################################################
# TRIAL CANCEL FLOW
########################################################################################################################

async def send_cancel_trial_confirm(interaction, trial, discord_server, trial_cache):
    """Check for blockers and show the cancel confirmation view."""
    # Hard error if any race has submissions
    if trial.current_race_id_id is not None:
        num_subs = get_num_submissions(trial.current_race_id_id)
        if num_subs > 0:
            await send_message(
                interaction,
                "Cannot cancel — this trial has races with submissions. "
                "Use `/async_mod end_trial` and `/async_mod archive_trial` instead.")
            return

    embed = nextcord.Embed(
        title=f"Cancel '{trial.display_name}'?",
        description="This will delete the participant role and announcement message.",
        color=nextcord.Colour.red())
    view = CancelTrialView(trial, discord_server, trial_cache)
    await send_message(interaction, embed=embed, view=view)

########################################################################################################################
class CancelTrialView(nextcord.ui.View):
    def __init__(self, trial, discord_server, trial_cache):
        super().__init__(timeout=300)
        self.trial = trial
        self.discord_server = discord_server
        self.trial_cache = trial_cache

    @nextcord.ui.button(label="Confirm Cancel", style=nextcord.ButtonStyle.danger)
    async def confirm(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self._do_cancel(interaction)
        self.stop()

    @nextcord.ui.button(label="Abort", style=nextcord.ButtonStyle.secondary)
    async def abort(self, button, interaction):
        await interaction.response.edit_message(content="Cancelled.", embed=None, view=None)
        self.stop()

    async def _do_cancel(self, interaction):
        results = []
        errors = []

        # Delete announcement message
        if self.trial.announcement_message_id and self.trial.announcement_channel_id:
            channel = self.discord_server.get_channel(self.trial.announcement_channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(self.trial.announcement_message_id)
                    await msg.delete()
                    results.append("Announcement message deleted")
                except Exception:
                    errors.append("Warning: Announcement message not found or already deleted")

        # Remove and delete participant role
        if self.trial.participant_role_id:
            role = self.discord_server.get_role(self.trial.participant_role_id)
            if role:
                try:
                    await role.delete(reason="Trial cancelled")
                    results.append("Participant role deleted")
                except Exception as e:
                    errors.append(f"Warning: Could not delete participant role: {e}")

        # Delete any associated race with no submissions (defensive; normally null in Announcing state)
        if self.trial.current_race_id_id is not None:
            try:
                AsyncRaceRoster.delete().where(
                    AsyncRaceRoster.race_id == self.trial.current_race_id_id).execute()
                AsyncRace.delete().where(
                    AsyncRace.id == self.trial.current_race_id_id).execute()
                results.append("Associated race deleted")
            except Exception as e:
                errors.append(f"Warning: Could not delete associated race: {e}")

        # Deactivate bot category if one was created (defensive; normally null in Announcing state)
        if self.trial.category_id_id is not None:
            try:
                cat = AsyncRaceCategory.get_by_id(self.trial.category_id_id)
                cat.active = False
                cat.save()
                results.append("Bot category deactivated")
            except Exception as e:
                errors.append(f"Warning: Could not deactivate category: {e}")

        # Remove from reaction cache
        if self.trial.announcement_message_id in self.trial_cache:
            del self.trial_cache[self.trial.announcement_message_id]

        # Delete Trial DB record
        try:
            self.trial.delete_instance()
            results.append("Trial record deleted")
        except Exception as e:
            errors.append(f"**ERROR** Could not delete trial record: {e}")

        summary_lines = results + errors
        summary = "\n".join(f"• {l}" for l in summary_lines) if summary_lines else "Nothing to clean up."
        await send_message(interaction, f"Trial cancelled.\n{summary}")

########################################################################################################################
# TRIAL END FLOW
########################################################################################################################

async def send_end_trial_confirm(interaction, trial, trial_cache):
    race_note = ""
    if trial.current_race_id_id is not None:
        try:
            race = AsyncRace.get_by_id(trial.current_race_id_id)
            if race.state == RaceState.Active:
                race_note = "\nThe current active race will be ended and scored."
        except Exception:
            pass

    embed = nextcord.Embed(
        title=f"End '{trial.display_name}'?",
        description=f"This will mark the trial as Ended.{race_note}",
        color=nextcord.Colour.orange())
    view = EndTrialView(trial, trial_cache)
    await send_message(interaction, embed=embed, view=view)

########################################################################################################################
class EndTrialView(nextcord.ui.View):
    def __init__(self, trial, trial_cache):
        super().__init__(timeout=300)
        self.trial = trial
        self.trial_cache = trial_cache

    @nextcord.ui.button(label="Confirm End Trial", style=nextcord.ButtonStyle.danger)
    async def confirm(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        results = []

        # End current race if still active
        if self.trial.current_race_id_id is not None:
            try:
                race = AsyncRace.get_by_id(self.trial.current_race_id_id)
                if race.state == RaceState.Active:
                    race.state = RaceState.Completed
                    race.save()
                    score_race(race)
                    await update_race_leaderboard(interaction, race)
                    results.append("Final race ended and scored")
            except Exception as e:
                results.append(f"Warning: could not end current race: {e}")

        self.trial.state         = TrialState.Ended
        self.trial.accept_signups = False
        self.trial.save()
        results.append(f"**{self.trial.display_name}** marked as Ended")

        if self.trial.announcement_message_id in self.trial_cache:
            del self.trial_cache[self.trial.announcement_message_id]
            results.append("Reaction tracking stopped")

        await send_message(interaction, "\n".join(f"• {r}" for r in results))
        self.stop()

    @nextcord.ui.button(label="Abort", style=nextcord.ButtonStyle.secondary)
    async def abort(self, button, interaction):
        await interaction.response.edit_message(content="Aborted.", embed=None, view=None)
        self.stop()

########################################################################################################################
# TRIAL START FLOW
########################################################################################################################

class TrialChannelNamesView(nextcord.ui.View):
    """Shows proposed general and spoilers channel names with [Edit Names] and [Create Channels] buttons."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow

    @nextcord.ui.button(label="Edit Names", style=nextcord.ButtonStyle.blurple)
    async def edit_names(self, button, interaction):
        modal = zModal(
            {
                'general': nextcord.ui.TextInput(
                    label="General Channel Name",
                    default_value=self.flow.general_channel_name,
                    required=True,
                    custom_id='general',
                    row=1),
                'spoilers': nextcord.ui.TextInput(
                    label="Spoilers Channel Name",
                    default_value=self.flow.spoilers_channel_name,
                    required=True,
                    custom_id='spoilers',
                    row=2),
            },
            self._on_edit,
            "Edit Channel Names")
        await interaction.response.send_modal(modal)

    async def _on_edit(self, interaction, modal):
        for child in modal.children:
            match child.custom_id:
                case 'general':  self.flow.general_channel_name  = child.value.strip().replace(' ', '-')
                case 'spoilers': self.flow.spoilers_channel_name = child.value.strip().replace(' ', '-')
        new_view = TrialChannelNamesView(self.flow)
        await send_message(
            interaction,
            f"Updated channel names:\n• General: `#{self.flow.general_channel_name}`\n• Spoilers: `#{self.flow.spoilers_channel_name}`\n\nClick **Next** to proceed.",
            view=new_view)

    @nextcord.ui.button(label="Next", style=nextcord.ButtonStyle.green)
    async def create_channels(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.flow.on_channels_confirmed(interaction)
        self.stop()

########################################################################################################################
class TrialCategorySettingsView(nextcord.ui.View):
    """Category settings view with dynamic toggle buttons and a [Confirm Settings] button."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow
        f = flow

        lb_on    = f.post_leaderboard
        mod_view = f.mod_can_view_leaderboard
        edit_off = f.disable_edit_time_limit
        forf_off = f.disable_auto_forfeit

        def _btn(label, style, row, cb):
            b = nextcord.ui.Button(label=label, style=style, row=row)
            b.callback = cb
            self.add_item(b)

        # Row 0: Post leaderboard toggle; LB type toggle (conditional on lb_on + points scoring)
        _btn(
            label=f"Post Leaderboard: {'✅' if lb_on else '❌'}",
            style=nextcord.ButtonStyle.green if lb_on else nextcord.ButtonStyle.grey,
            row=0, cb=self._toggle_post_lb)

        if lb_on and f.points_type != PointsType.NoScoring:
            lb_type_str = "Points" if f.leaderboard_type == RaceLeaderboardType.Points else "Recent Race"
            _btn(label=f"LB Type: {lb_type_str}", style=nextcord.ButtonStyle.blurple, row=0, cb=self._toggle_lb_type)

        # Row 1: Three boolean toggles
        _btn(
            label=f"Mods View LB: {'✅' if mod_view else '❌'}",
            style=nextcord.ButtonStyle.green if mod_view else nextcord.ButtonStyle.grey,
            row=1, cb=self._toggle_mod_view)
        _btn(
            label=f"Disable Edit Timeout: {'✅' if edit_off else '❌'}",
            style=nextcord.ButtonStyle.green if edit_off else nextcord.ButtonStyle.grey,
            row=1, cb=self._toggle_edit_timeout)
        _btn(
            label=f"Disable Auto-Forfeit: {'✅' if forf_off else '❌'}",
            style=nextcord.ButtonStyle.green if forf_off else nextcord.ButtonStyle.grey,
            row=1, cb=self._toggle_auto_forfeit)

        # Row 2: Confirm
        _btn(label="Confirm Settings", style=nextcord.ButtonStyle.green, row=2, cb=self._confirm)

    async def _refresh(self, interaction):
        new_view = TrialCategorySettingsView(self.flow)
        await send_message(interaction, embed=self._build_embed(), view=new_view)

    async def _toggle_post_lb(self, interaction):
        self.flow.post_leaderboard = not self.flow.post_leaderboard
        await self._refresh(interaction)

    async def _toggle_lb_type(self, interaction):
        if self.flow.leaderboard_type == RaceLeaderboardType.Points:
            self.flow.leaderboard_type = RaceLeaderboardType.RecentRace
        else:
            self.flow.leaderboard_type = RaceLeaderboardType.Points
        await self._refresh(interaction)

    async def _toggle_mod_view(self, interaction):
        self.flow.mod_can_view_leaderboard = not self.flow.mod_can_view_leaderboard
        await self._refresh(interaction)

    async def _toggle_edit_timeout(self, interaction):
        self.flow.disable_edit_time_limit = not self.flow.disable_edit_time_limit
        await self._refresh(interaction)

    async def _toggle_auto_forfeit(self, interaction):
        self.flow.disable_auto_forfeit = not self.flow.disable_auto_forfeit
        await self._refresh(interaction)

    async def _confirm(self, interaction):
        await interaction.response.defer(ephemeral=True)
        if self.flow.post_leaderboard:
            lb_type_str = "Most Recent Race (restricted to finishers)" if self.flow.leaderboard_type == RaceLeaderboardType.RecentRace else "Points (open to all)"
            view = TrialLeaderboardChannelView(self.flow)
            await send_message(
                interaction,
                f"Leaderboard type: **{lb_type_str}**\n"
                f"Create a new dedicated leaderboard channel, or use an existing one?",
                view=view)
        else:
            await self.flow.on_settings_confirmed(interaction)
        self.stop()

    def _build_embed(self):
        f = self.flow
        embed = nextcord.Embed(title="Bot Category Settings", color=nextcord.Colour.blurple())
        embed.add_field(name="Scoring",               value=PointsType.to_str(f.points_type),              inline=True)
        embed.add_field(name="Post Leaderboard",      value="✅" if f.post_leaderboard else "❌",           inline=True)
        if f.post_leaderboard and f.points_type != PointsType.NoScoring:
            embed.add_field(name="LB Type",           value=RaceLeaderboardType.to_str(f.leaderboard_type), inline=True)
        embed.add_field(name="Mods View LB",          value="✅" if f.mod_can_view_leaderboard else "❌",   inline=True)
        embed.add_field(name="Disable Edit Timeout",  value="✅" if f.disable_edit_time_limit else "❌",    inline=True)
        embed.add_field(name="Disable Auto-Forfeit",  value="✅" if f.disable_auto_forfeit else "❌",       inline=True)
        return embed

########################################################################################################################
class TrialLeaderboardChannelView(nextcord.ui.View):
    """Asks whether to create a new leaderboard channel or link an existing one."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow

    @nextcord.ui.button(label="Create New Channel", style=nextcord.ButtonStyle.green)
    async def create_new(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        self.flow.leaderboard_channel_choice = 'create'
        await self.flow.on_settings_confirmed(interaction)
        self.stop()

    @nextcord.ui.button(label="Use Existing Channel", style=nextcord.ButtonStyle.blurple)
    async def use_existing(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        view = TrialLeaderboardChannelSelectView(self.flow)
        await send_message(interaction, "Select the channel to post the leaderboard in:", view=view)
        self.stop()

########################################################################################################################
class TrialLeaderboardChannelSelectView(nextcord.ui.View):
    """Channel select for picking an existing leaderboard channel."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow

    @nextcord.ui.channel_select(placeholder="Select leaderboard channel...",
                                channel_types=[nextcord.ChannelType.text])
    async def channel_select(self, select, interaction):
        await interaction.response.defer(ephemeral=True)
        self.flow.leaderboard_channel_choice = select.values[0].id
        await self.flow.on_settings_confirmed(interaction)
        self.stop()

########################################################################################################################
class TrialExtraInfoRequiredView(nextcord.ui.View):
    """Asks whether a newly-added extra info type should be required or optional."""

    def __init__(self, flow, assignment, type_name):
        super().__init__(timeout=300)
        self.flow = flow
        self.assignment = assignment
        self.type_name = type_name

    @nextcord.ui.button(label="Required", style=nextcord.ButtonStyle.red)
    async def required(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        self.assignment.required = True
        self.assignment.save()
        view = TrialExtraInfoYesNoView(self.flow, "")
        await send_message(interaction, f"Added **{self.type_name}** as **required**.", view=view)
        self.stop()

    @nextcord.ui.button(label="Optional", style=nextcord.ButtonStyle.blurple)
    async def optional(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        self.assignment.required = False
        self.assignment.save()
        view = TrialExtraInfoYesNoView(self.flow, "")
        await send_message(interaction, f"Added **{self.type_name}** as **optional**.", view=view)
        self.stop()

########################################################################################################################
class TrialExtraInfoYesNoView(nextcord.ui.View):
    """Asks whether to add another extra info field to the trial's bot category."""

    def __init__(self, flow, prompt_text):
        super().__init__(timeout=300)
        self.flow = flow
        self.prompt_text = prompt_text

    @nextcord.ui.button(label="Edit Extra Info", style=nextcord.ButtonStyle.green)
    async def yes(self, button, interaction):
        await self.flow.on_add_extra_info(interaction)
        self.stop()

    @nextcord.ui.button(label="Done", style=nextcord.ButtonStyle.grey)
    async def no(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.flow.on_extra_info_done(interaction)
        self.stop()

########################################################################################################################
class TrialPartialStartView(nextcord.ui.View):
    """Shown when a trial has partial start state (some Discord objects were created but the flow was abandoned)."""

    def __init__(self, trial, db_server, discord_server):
        super().__init__(timeout=300)
        self.trial = trial
        self.db_server = db_server
        self.discord_server = discord_server

    @nextcord.ui.button(label="Rollback Partial Start", style=nextcord.ButtonStyle.red)
    async def rollback(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        trial = self.trial
        cleanup = []

        if trial.general_channel_id:
            try:
                ch = await self.discord_server.fetch_channel(trial.general_channel_id)
            except nextcord.errors.NotFound:
                logging.warning(f"Partial rollback trial '{trial.display_name}': general channel {trial.general_channel_id} not found in Discord")
                cleanup.append("general channel not found (may have been deleted already)")
            except Exception as e:
                logging.error(f"Partial rollback trial '{trial.display_name}': could not fetch general channel {trial.general_channel_id}: {e}")
                cleanup.append(f"could not fetch general channel: {e}")
            else:
                try:
                    await ch.delete(reason="Trial start rollback")
                    cleanup.append("general channel deleted")
                except Exception as e:
                    logging.error(f"Partial rollback trial '{trial.display_name}': could not delete general channel {trial.general_channel_id}: {e}")
                    cleanup.append(f"could not delete general channel: {e}")
            trial.general_channel_id = None

        if trial.spoilers_channel_id:
            try:
                ch = await self.discord_server.fetch_channel(trial.spoilers_channel_id)
            except nextcord.errors.NotFound:
                logging.warning(f"Partial rollback trial '{trial.display_name}': spoilers channel {trial.spoilers_channel_id} not found in Discord")
                cleanup.append("spoilers channel not found (may have been deleted already)")
            except Exception as e:
                logging.error(f"Partial rollback trial '{trial.display_name}': could not fetch spoilers channel {trial.spoilers_channel_id}: {e}")
                cleanup.append(f"could not fetch spoilers channel: {e}")
            else:
                try:
                    await ch.delete(reason="Trial start rollback")
                    cleanup.append("spoilers channel deleted")
                except Exception as e:
                    logging.error(f"Partial rollback trial '{trial.display_name}': could not delete spoilers channel {trial.spoilers_channel_id}: {e}")
                    cleanup.append(f"could not delete spoilers channel: {e}")
            trial.spoilers_channel_id = None

        if trial.finisher_role_id:
            role = self.discord_server.get_role(trial.finisher_role_id)
            if role:
                try:
                    await role.delete(reason="Trial start rollback")
                    cleanup.append("finisher role deleted")
                except Exception as e:
                    logging.error(f"Partial rollback trial '{trial.display_name}': could not delete finisher role {trial.finisher_role_id}: {e}")
                    cleanup.append(f"could not delete finisher role: {e}")
            else:
                logging.warning(f"Partial rollback trial '{trial.display_name}': finisher role {trial.finisher_role_id} not found in cache")
                cleanup.append("finisher role not found (may have been deleted already)")
            trial.finisher_role_id = None

        if trial.category_id:
            try:
                cat = AsyncRaceCategory.get_by_id(trial.category_id)
                for a in get_category_extra_info_assignments(cat.id):
                    a.delete_instance()
                cat.delete_instance()
                cleanup.append("bot category deleted")
            except Exception as e:
                cleanup.append(f"could not delete bot category: {e}")
            trial.category_id = None

        if trial.leaderboard_channel_id:
            try:
                ch = await self.discord_server.fetch_channel(trial.leaderboard_channel_id)
            except nextcord.errors.NotFound:
                logging.warning(f"Partial rollback trial '{trial.display_name}': leaderboard channel {trial.leaderboard_channel_id} not found in Discord")
                cleanup.append("leaderboard channel not found (may have been deleted already)")
            except Exception as e:
                logging.error(f"Partial rollback trial '{trial.display_name}': could not fetch leaderboard channel {trial.leaderboard_channel_id}: {e}")
                cleanup.append(f"could not fetch leaderboard channel: {e}")
            else:
                try:
                    await ch.delete(reason="Trial start rollback")
                    cleanup.append("leaderboard channel deleted")
                except Exception as e:
                    logging.error(f"Partial rollback trial '{trial.display_name}': could not delete leaderboard channel {trial.leaderboard_channel_id}: {e}")
                    cleanup.append(f"could not delete leaderboard channel: {e}")
            trial.leaderboard_channel_id = None

        trial.save()
        detail = "\n".join(f"• {c}" for c in cleanup) if cleanup else "• Nothing to clean up"
        await send_message(interaction, f"Rollback complete:\n{detail}\n\nRun `/async_mod start_trial` again to restart.")
        self.stop()

    @nextcord.ui.button(label="Continue Setup", style=nextcord.ButtonStyle.green)
    async def continue_setup(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        trial = self.trial

        # Resolve Discord objects from cached IDs
        general_channel  = self.discord_server.get_channel(trial.general_channel_id)  if trial.general_channel_id  else None
        spoilers_channel = self.discord_server.get_channel(trial.spoilers_channel_id) if trial.spoilers_channel_id else None
        finisher_role    = self.discord_server.get_role(trial.finisher_role_id)        if trial.finisher_role_id    else None
        leaderboard_channel = self.discord_server.get_channel(trial.leaderboard_channel_id) if trial.leaderboard_channel_id else None
        category = None
        if trial.category_id:
            try:
                category = AsyncRaceCategory.get_by_id(trial.category_id)
            except Exception:
                pass

        missing = []
        if not general_channel:  missing.append("general channel")
        if not spoilers_channel: missing.append("spoilers channel")
        if not finisher_role:    missing.append("finisher role")
        if not category:         missing.append("bot category")
        if missing:
            await send_message(interaction, f"Cannot continue — could not resolve: {', '.join(missing)}.\nUse **Rollback Partial Start** to clean up and restart.")
            return

        flow = TrialStartFlow(trial, self.db_server, self.discord_server)
        flow.general_channel     = general_channel
        flow.spoilers_channel    = spoilers_channel
        flow.finisher_role       = finisher_role
        flow.category            = category
        flow.leaderboard_channel = leaderboard_channel

        view = TrialExtraInfoYesNoView(flow, "")
        await send_message(interaction, "Resuming trial setup — add extra submission fields beyond Finish Time and Comment?", view=view)
        self.stop()

########################################################################################################################
class TrialStartFlow:
    """Orchestrates the multi-step /start_trial flow: channels → finisher role → category settings → extra info → save."""

    def __init__(self, trial, db_server, discord_server):
        self.trial = trial
        self.db_server = db_server
        self.discord_server = discord_server
        # Proposed names
        base = trial.short_name.lower().replace(' ', '-')
        self.general_channel_name  = base
        self.spoilers_channel_name = f"{base}-spoilers"
        self.finisher_role_name    = f"{trial.short_name} Finisher"
        # Category settings (defaults)
        self.points_type              = PointsType.NoScoring
        self.post_leaderboard         = False
        self.leaderboard_type         = RaceLeaderboardType.RecentRace
        self.mod_can_view_leaderboard = True
        self.disable_edit_time_limit  = False
        self.disable_auto_forfeit     = True
        # Created objects (tracked for rollback)
        self.general_channel         = None
        self.spoilers_channel        = None
        self.finisher_role           = None
        self.category                = None
        self.leaderboard_channel     = None
        self.leaderboard_channel_choice = None  # 'create' or int channel_id

    # ------------------------------------------------------------------------------------------------------------------
    async def start(self, interaction):
        count = 0
        if self.trial.participant_role_id:
            role = self.discord_server.get_role(self.trial.participant_role_id)
            if role:
                count = len(role.members)

        view = TrialChannelNamesView(self)
        await send_message(
            interaction,
            f"**Starting trial: {self.trial.display_name}**\n"
            f"Current signups: **{count}**\n\n"
            f"Proposed channel names:\n"
            f"• General: `#{self.general_channel_name}`\n"
            f"• Spoilers: `#{self.spoilers_channel_name}`\n\n"
            f"Click **Edit Names** to change or **Next** to proceed.",
            view=view)

    # ------------------------------------------------------------------------------------------------------------------
    async def on_channels_confirmed(self, interaction):
        view = TrialRoleNameView(self, self.finisher_role_name)
        await send_message(
            interaction,
            f"Proposed finisher role name: **{self.finisher_role_name}**\nClick **Edit Name** to change or **Next** to proceed.",
            view=view)

    # Called by TrialRoleNameView (reused from announce flow)
    async def on_role_name_confirmed(self, interaction, role_name):
        self.finisher_role_name = role_name
        select_list = copy.deepcopy(PointsType.SelectOptionList)
        selected = await zSingleSelectView(select_list, None, "Select scoring type...").prompt(interaction)
        if selected is None:
            await self._rollback(interaction, "Scoring type selection timed out.")
            return
        self.points_type = selected

        view = TrialCategorySettingsView(self)
        await send_message(
            interaction,
            "Review the bot category settings below. Click any toggle button to change it, then click **Confirm Settings** when done.",
            embed=view._build_embed(),
            view=view)

    # ------------------------------------------------------------------------------------------------------------------
    async def on_settings_confirmed(self, interaction):
        discord_category = self.discord_server.get_channel(self.db_server.trials_discord_category_id)
        admin_role = self.discord_server.get_role(self.db_server.admin_role_id) if self.db_server.admin_role_id else None

        # Create general channel (visible to everyone in the Discord category)
        try:
            self.general_channel = await self.discord_server.create_text_channel(
                name=self.general_channel_name,
                category=discord_category,
                reason=f"Trial: {self.trial.display_name}")
            self.trial.general_channel_id = self.general_channel.id
            self.trial.save()
        except Exception as e:
            await self._rollback(interaction, f"Could not create general channel: {e}")
            return

        # Create spoilers channel (viewable only by finisher role and admin role)
        # Bot must have an explicit allow overwrite or it loses access when @everyone is denied,
        # which would cause the subsequent set_permissions call to fail with 50001.
        try:
            overwrites = {
                self.discord_server.default_role: nextcord.PermissionOverwrite(read_messages=False),
                self.discord_server.me: nextcord.PermissionOverwrite(read_messages=True),
            }
            if admin_role:
                overwrites[admin_role] = nextcord.PermissionOverwrite(read_messages=True)
            self.spoilers_channel = await self.discord_server.create_text_channel(
                name=self.spoilers_channel_name,
                category=discord_category,
                overwrites=overwrites,
                reason=f"Trial: {self.trial.display_name}")
            self.trial.spoilers_channel_id = self.spoilers_channel.id
            self.trial.save()
        except Exception as e:
            await self._rollback(interaction, f"Could not create spoilers channel: {e}")
            return

        # Create finisher role
        try:
            self.finisher_role = await self.discord_server.create_role(
                name=self.finisher_role_name,
                reason=f"Trial finisher role: {self.trial.display_name}")
            self.trial.finisher_role_id = self.finisher_role.id
            self.trial.save()
        except Exception as e:
            await self._rollback(interaction, f"Could not create finisher role: {e}")
            return

        # Grant finisher role access to spoilers channel
        try:
            await self.spoilers_channel.set_permissions(
                self.finisher_role,
                read_messages=True)
        except Exception as e:
            await self._rollback(interaction, f"Could not set spoilers channel permissions: {e}")
            return

        # Create bot category
        try:
            cat = AsyncRaceCategory()
            cat.server_id                = self.db_server.id
            cat.name                     = self.trial.display_name
            cat.description              = self.trial.short_description or ''
            cat.points_type              = self.points_type
            cat.leaderboard_type         = self.leaderboard_type if self.post_leaderboard else None
            cat.active                   = True
            cat.pin_recent_race          = False
            cat.activate_new_races       = False
            cat.submit_role              = self.finisher_role.id
            cat.mod_can_view_leaderboard = self.mod_can_view_leaderboard
            cat.disable_edit_time_limit  = self.disable_edit_time_limit
            cat.disable_auto_forfeit     = self.disable_auto_forfeit
            cat.save()
            self.category = cat
            self.trial.category_id = self.category.id
            self.trial.save()
        except Exception as e:
            await self._rollback(interaction, f"Could not create bot category: {e}")
            return

        if self.points_type == PointsType.Trueskill:
            try:
                create_default_trueskill_params(self.category.id)
            except Exception as e:
                logging.warning(f"Could not create TrueSkill params for trial category: {e}")

        # Create or link leaderboard channel (if leaderboard posting is enabled)
        if self.post_leaderboard and self.leaderboard_channel_choice is not None:
            if self.leaderboard_channel_choice == 'create':
                try:
                    lb_name = f"{self.general_channel_name}-leaderboard"
                    if self.leaderboard_type == RaceLeaderboardType.RecentRace:
                        lb_overwrites = {
                            self.discord_server.default_role: nextcord.PermissionOverwrite(read_messages=False),
                            self.discord_server.me: nextcord.PermissionOverwrite(read_messages=True),
                            self.finisher_role: nextcord.PermissionOverwrite(read_messages=True),
                        }
                        if admin_role:
                            lb_overwrites[admin_role] = nextcord.PermissionOverwrite(read_messages=True)
                    else:
                        lb_overwrites = {}
                    self.leaderboard_channel = await self.discord_server.create_text_channel(
                        name=lb_name,
                        category=discord_category,
                        overwrites=lb_overwrites,
                        reason=f"Trial leaderboard: {self.trial.display_name}")
                    self.trial.leaderboard_channel_id = self.leaderboard_channel.id
                    self.trial.save()
                except Exception as e:
                    await self._rollback(interaction, f"Could not create leaderboard channel: {e}")
                    return
            else:
                # User selected an existing channel — resolve it but do NOT store the ID on trial
                self.leaderboard_channel = self.discord_server.get_channel(self.leaderboard_channel_choice)

            if self.leaderboard_channel:
                try:
                    await post_channel_category_leaderboard(interaction, self.leaderboard_channel, self.category.id, interaction.client)
                except Exception as e:
                    logging.warning(f"Could not post initial leaderboard for trial '{self.trial.display_name}': {e}")

        # Start extra info loop
        view = TrialExtraInfoYesNoView(self, "")
        await send_message(
            interaction,
            "Configure extra submission fields beyond Finish Time and Comment? Click **Edit Extra Info** to add or remove fields, or **Done** to finish.",
            view=view)

    # ------------------------------------------------------------------------------------------------------------------
    async def on_add_extra_info(self, interaction):
        assigned_ids = {a.info_type_id_id for a in get_category_extra_info_assignments(self.category.id)}
        select_list = get_extra_info_type_select_list(self.db_server.id)
        for opt in select_list:
            if int(opt.value) in assigned_ids:
                opt.label = f"✅ {opt.label}"
        select_list.insert(0, nextcord.SelectOption(
            label="Create New...", value='0', description="Define a new extra info type"))

        view = nextcord.ui.View(timeout=300)
        select = zSingleSelect(select_list, self._on_extra_info_selected, "Select an extra info type to add or remove...", None)
        view.add_item(select)
        await send_message(interaction, "Select an extra info type to add or remove:", view=view)

    async def _on_extra_info_selected(self, selected_id, interaction):
        if selected_id == 0:
            # Open modal to create new extra info type
            modal = zModal(
                {
                    'name': nextcord.ui.TextInput(
                        label="Type Name", required=True, custom_id='name', row=1),
                    'desc': nextcord.ui.TextInput(
                        label="Type Description", required=False, custom_id='desc', row=2),
                },
                self._on_extra_info_name_submit,
                "New Extra Info Type")
            await interaction.response.send_modal(modal)
        else:
            type_obj = get_extra_info_type(selected_id)
            name = type_obj.name if type_obj else f"ID {selected_id}"
            if check_category_assignment_exists(selected_id, self.category.id):
                delete_category_assignment(selected_id, self.category.id)
                view = TrialExtraInfoYesNoView(self, "")
                await send_message(interaction, f"Removed **{name}**.", view=view)
            else:
                assignment = AsyncRaceExtraInfoAssignment(
                    info_type_id=selected_id, category_id=self.category.id)
                view = TrialExtraInfoRequiredView(self, assignment, name)
                await send_message(interaction, f"Should **{name}** be required or optional?", view=view)

    async def _on_extra_info_name_submit(self, interaction, modal):
        self._pending_info_name = ""
        self._pending_info_desc = ""
        for child in modal.children:
            match child.custom_id:
                case 'name': self._pending_info_name = child.value.strip()
                case 'desc': self._pending_info_desc = child.value.strip()

        select_list = copy.deepcopy(VarType.SelectOptionList)
        view = nextcord.ui.View(timeout=300)
        select = zSingleSelect(select_list, self._on_extra_info_vartype_selected, "Select data type...", None)
        view.add_item(select)
        await send_message(interaction, f"Select data type for **{self._pending_info_name}**:", view=view)

    async def _on_extra_info_vartype_selected(self, vartype, interaction):
        try:
            info_type = AsyncRaceExtraInfoType()
            info_type.server_id      = self.db_server.id
            info_type.name           = self._pending_info_name
            info_type.description    = self._pending_info_desc
            info_type.var_type       = vartype
            info_type.save()
            assignment = AsyncRaceExtraInfoAssignment(
                info_type_id=info_type.id, category_id=self.category.id)
            view = TrialExtraInfoRequiredView(self, assignment, info_type.name)
            await send_message(
                interaction,
                f"Created **{info_type.name}**. Should it be required or optional?",
                view=view)
        except Exception as e:
            view = TrialExtraInfoYesNoView(self, "")
            await send_message(
                interaction,
                f"**ERROR** Could not save extra info type: {e}",
                view=view)

    # ------------------------------------------------------------------------------------------------------------------
    async def on_extra_info_done(self, interaction):
        try:
            self.trial.general_channel_id  = self.general_channel.id
            self.trial.spoilers_channel_id = self.spoilers_channel.id
            self.trial.finisher_role_id    = self.finisher_role.id
            self.trial.category_id         = self.category.id
            self.trial.state               = TrialState.Active
            self.trial.save()
        except Exception as e:
            await send_message(interaction, f"**ERROR** Could not update trial record: {e}")
            return

        lb_line = f"\n• Leaderboard: <#{self.trial.leaderboard_channel_id}>" if self.trial.leaderboard_channel_id else ""
        await send_message(
            interaction,
            f"Trial **{self.trial.display_name}** is now Active!\n"
            f"• General: <#{self.general_channel.id}>\n"
            f"• Spoilers: <#{self.spoilers_channel.id}>\n"
            f"• Finisher role: {self.finisher_role.mention}\n"
            f"• Bot category ID: {self.category.id}"
            f"{lb_line}")

    # ------------------------------------------------------------------------------------------------------------------
    async def _rollback(self, interaction, error_msg):
        logging.error(f"Trial start rollback triggered for '{self.trial.display_name}': {error_msg}")
        cleanup = []
        if self.general_channel:
            try:
                await self.general_channel.delete(reason="Trial start failed/cancelled")
                cleanup.append("general channel deleted")
            except Exception as e:
                logging.error(f"Trial start rollback '{self.trial.display_name}': could not delete general channel: {e}")
                cleanup.append(f"could not delete general channel: {e}")
            self.general_channel = None
        if self.spoilers_channel:
            try:
                await self.spoilers_channel.delete(reason="Trial start failed/cancelled")
                cleanup.append("spoilers channel deleted")
            except Exception as e:
                logging.error(f"Trial start rollback '{self.trial.display_name}': could not delete spoilers channel: {e}")
                cleanup.append(f"could not delete spoilers channel: {e}")
            self.spoilers_channel = None
        if self.finisher_role:
            try:
                await self.finisher_role.delete(reason="Trial start failed/cancelled")
                cleanup.append("finisher role deleted")
            except Exception as e:
                logging.error(f"Trial start rollback '{self.trial.display_name}': could not delete finisher role: {e}")
                cleanup.append(f"could not delete finisher role: {e}")
            self.finisher_role = None
        if self.category:
            try:
                for a in get_category_extra_info_assignments(self.category.id):
                    a.delete_instance()
                self.category.delete_instance()
                cleanup.append("bot category deleted")
            except Exception as e:
                logging.error(f"Trial start rollback '{self.trial.display_name}': could not delete bot category: {e}")
                cleanup.append(f"could not delete bot category: {e}")
            self.category = None
        if self.leaderboard_channel and self.trial.leaderboard_channel_id:
            try:
                await self.leaderboard_channel.delete(reason="Trial start failed/cancelled")
                cleanup.append("leaderboard channel deleted")
            except Exception as e:
                logging.error(f"Trial start rollback '{self.trial.display_name}': could not delete leaderboard channel: {e}")
                cleanup.append(f"could not delete leaderboard channel: {e}")
            self.leaderboard_channel = None

        # Clear partial IDs from trial record so a retry starts clean
        self.trial.general_channel_id     = None
        self.trial.spoilers_channel_id    = None
        self.trial.finisher_role_id       = None
        self.trial.category_id            = None
        self.trial.leaderboard_channel_id = None
        self.trial.save()

        detail = "\n".join(f"• {c}" for c in cleanup)
        msg = f"**ERROR** {error_msg}"
        if detail:
            msg += f"\n\nRolled back:\n{detail}"
        await send_message(interaction, msg)

########################################################################################################################
# PHASE 3 — TRIAL RACE LIFECYCLE
########################################################################################################################

def user_can_manage_trial(interaction, trial):
    """Returns True if the user is a mod/admin or the trial's designated organizer."""
    return user_is_mod(interaction.guild, interaction.user) or \
           (trial.organizer_user_id is not None and interaction.user.id == trial.organizer_user_id)

########################################################################################################################
class TrialSignupView(nextcord.ui.View):
    """Asks whether to close signups before starting the next race."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow

    @nextcord.ui.button(label="Close Signups", style=nextcord.ButtonStyle.red)
    async def close_signups(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        self.flow.close_signups = True
        await send_message(interaction, "Review the participant list before starting the race.",
                           view=TrialRacerManagementView(self.flow))
        self.stop()

    @nextcord.ui.button(label="Keep Signups Open", style=nextcord.ButtonStyle.green)
    async def keep_signups(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        self.flow.close_signups = False
        await send_message(interaction, "Review the participant list before starting the race.",
                           view=TrialRacerManagementView(self.flow))
        self.stop()

########################################################################################################################
class TrialRaceDetailsModal(zModal):
    def __init__(self, submit_handler):
        fields = {
            'description': nextcord.ui.TextInput(
                label="Race Description", required=True, custom_id='description', row=1),
            'seed': nextcord.ui.TextInput(
                label="Seed", required=True, custom_id='seed', row=2),
            'hash': nextcord.ui.TextInput(
                label="Hash (optional)", required=False, custom_id='hash', row=3),
            'instructions': nextcord.ui.TextInput(
                label="Additional Instructions (optional)", required=False,
                custom_id='instructions', row=4,
                style=nextcord.TextInputStyle.paragraph),
        }
        super().__init__(fields, submit_handler, "Race Details")

########################################################################################################################
class TrialRacerManagementView(nextcord.ui.View):
    """Lets the organizer add/remove participants before the race is created."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow

    def _participant_count(self):
        role = self.flow.discord_server.get_role(self.flow.trial.participant_role_id) \
               if self.flow.trial.participant_role_id else None
        return len(role.members) if role else 0

    @nextcord.ui.button(label="Add Racer", style=nextcord.ButtonStyle.green)
    async def add_racer(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await send_message(
            interaction,
            f"Select a member to add as a participant ({self._participant_count()} currently signed up):",
            view=TrialAddRacerView(self.flow))
        self.stop()

    @nextcord.ui.button(label="Remove Racer", style=nextcord.ButtonStyle.red)
    async def remove_racer(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        role = self.flow.discord_server.get_role(self.flow.trial.participant_role_id) \
               if self.flow.trial.participant_role_id else None
        if not role or not role.members:
            await send_message(interaction, "No participants to remove.", view=TrialRacerManagementView(self.flow))
            self.stop()
            return
        select_list = [
            nextcord.SelectOption(label=m.display_name, value=str(m.id))
            for m in sorted(role.members, key=lambda m: m.display_name)[:25]
        ]
        select = zSingleSelect(select_list, self.flow._on_remove_racer_selected,
                               "Select a participant to remove...", None)
        view = nextcord.ui.View(timeout=300)
        view.add_item(select)
        await send_message(
            interaction,
            f"Select a participant to remove ({self._participant_count()} currently signed up):",
            view=view)
        self.stop()

    @nextcord.ui.button(label="Done", style=nextcord.ButtonStyle.blurple)
    async def done(self, button, interaction):
        await interaction.response.send_modal(TrialRaceDetailsModal(self.flow._on_race_details_submit))
        self.stop()

########################################################################################################################
class TrialAddRacerView(nextcord.ui.View):
    """Discord UserSelect for adding a member to the trial participant role."""

    def __init__(self, flow):
        super().__init__(timeout=300)
        self.flow = flow

    @nextcord.ui.user_select(placeholder="Select member to add as participant...")
    async def user_select(self, select, interaction):
        await interaction.response.defer(ephemeral=True)
        member = select.values[0]
        participant_role = self.flow.discord_server.get_role(self.flow.trial.participant_role_id) \
                           if self.flow.trial.participant_role_id else None
        if participant_role is None:
            await send_message(interaction, "Participant role not found.", view=TrialRacerManagementView(self.flow))
            self.stop()
            return
        if participant_role in member.roles:
            await send_message(interaction, f"**{member.display_name}** is already a participant.",
                               view=TrialRacerManagementView(self.flow))
            self.stop()
            return
        try:
            await member.add_roles(participant_role, reason=f"Added to trial {self.flow.trial.display_name}")
            await send_message(interaction, f"Added **{member.display_name}** as a participant.",
                               view=TrialRacerManagementView(self.flow))
        except Exception as e:
            await send_message(interaction, f"Could not add **{member.display_name}**: {e}",
                               view=TrialRacerManagementView(self.flow))
        self.stop()

########################################################################################################################
class TrialStartRaceFlow:
    """Orchestrates the /start_trial_race flow: end previous race → signup prompt → race details → create & activate."""

    def __init__(self, trial, db_server, discord_server):
        self.trial          = trial
        self.db_server      = db_server
        self.discord_server = discord_server
        self.close_signups  = True
        self.description    = ""
        self.seed           = ""
        self.hash           = None
        self.instructions   = None

    async def start(self, interaction):
        prev_text = ""
        if self.trial.current_race_id_id is not None:
            try:
                prev_race = AsyncRace.get_by_id(self.trial.current_race_id_id)
                if prev_race.state == RaceState.Active:
                    prev_race.state = RaceState.Completed
                    prev_race.save()
                    score_race(prev_race)
                    await update_race_leaderboard(interaction, prev_race)
                    prev_text = "Previous race ended.\n\n"
            except Exception as e:
                prev_text = f"Warning: could not end previous race: {e}\n\n"

        participant_role = self.discord_server.get_role(self.trial.participant_role_id) \
                           if self.trial.participant_role_id else None
        participant_count = len(participant_role.members) if participant_role else 0
        view = TrialSignupView(self)
        await send_message(
            interaction,
            f"{prev_text}**{self.trial.display_name}** — {participant_count} participant(s) signed up. Close signups for the new race?",
            view=view)

    async def _on_remove_racer_selected(self, selected_id, interaction):
        await interaction.response.defer(ephemeral=True)
        participant_role = self.discord_server.get_role(self.trial.participant_role_id) \
                           if self.trial.participant_role_id else None
        if participant_role is None:
            await send_message(interaction, "Participant role not found.", view=TrialRacerManagementView(self))
            return
        member = self.discord_server.get_member(selected_id)
        if member is None:
            await send_message(interaction, "Member not found.", view=TrialRacerManagementView(self))
            return
        try:
            await member.remove_roles(participant_role, reason=f"Removed from trial {self.trial.display_name}")
            await send_message(interaction, f"Removed **{member.display_name}** from participants.",
                               view=TrialRacerManagementView(self))
        except Exception as e:
            await send_message(interaction, f"Could not remove **{member.display_name}**: {e}",
                               view=TrialRacerManagementView(self))

    async def _on_race_details_submit(self, interaction, modal):
        for child in modal.children:
            match child.custom_id:
                case 'description':  self.description  = child.value.strip()
                case 'seed':         self.seed         = child.value.strip()
                case 'hash':         self.hash         = child.value.strip() or None
                case 'instructions': self.instructions = child.value.strip() or None
        await interaction.response.defer(ephemeral=True)
        await self._create_and_activate(interaction)

    async def _create_and_activate(self, interaction):
        # Build the new race record
        race = AsyncRace()
        race.server_id            = self.db_server.id
        race.create_datetime      = zBot_now()
        race.seed                    = self.seed
        race.hash                    = self.hash
        race.description             = self.description
        race.additional_instructions = self.instructions
        race.category_id             = self.trial.category_id_id
        race.state                   = RaceState.Inactive
        race.disable_auto_forfeit    = self.trial.category_id.disable_auto_forfeit
        race.save()

        # Copy extra info assignments from category
        for a in get_category_extra_info_assignments(self.trial.category_id_id):
            ra = AsyncRaceExtraInfoAssignment()
            ra.info_type_id = a.info_type_id
            ra.race_id      = race.id
            ra.required     = a.required
            ra.save()

        # Auto-assign all current participant role holders
        assigned_count = 0
        participant_role = self.discord_server.get_role(self.trial.participant_role_id) if self.trial.participant_role_id else None
        if participant_role:
            for member in participant_role.members:
                if assign_racer(member.id, race.id):
                    assigned_count += 1

        # Apply signup decision and activate
        self.trial.accept_signups   = not self.close_signups
        race.state                  = RaceState.Active
        race.save()
        self.trial.current_race_id  = race.id
        self.trial.save()

        await handle_activate_race(interaction, race)

        # Post race info to general channel
        general_channel = self.discord_server.get_channel(self.trial.general_channel_id) if self.trial.general_channel_id else None
        if general_channel:
            try:
                await post_race_info_message(race, general_channel)
            except Exception as e:
                await send_message(interaction, f"Warning: could not post race info to general channel: {e}")

        signup_status = "Signups closed" if self.close_signups else "Signups remain open"
        await send_message(
            interaction,
            f"Race started for **{self.trial.display_name}**!\n"
            f"• Description: {self.description}\n"
            f"• {assigned_count} participant(s) assigned\n"
            f"• {signup_status}"
            + (f"\n• Race info posted in <#{self.trial.general_channel_id}>" if general_channel else ""))

########################################################################################################################
# PHASE 4 — TRIAL ARCHIVE
########################################################################################################################

async def send_archive_trial_prompt(interaction, trial, discord_server, trial_cache):
    embed = nextcord.Embed(
        title=f"Archive '{trial.display_name}'",
        description="Select what to remove. The bot category is always deactivated (not deleted — race history is preserved). Dismiss this message to abort.",
        color=nextcord.Colour.blurple())

    ch_lines = []
    if trial.general_channel_id:
        ch_lines.append(f"<#{trial.general_channel_id}> (general)")
    if trial.spoilers_channel_id:
        ch_lines.append(f"<#{trial.spoilers_channel_id}> (spoilers)")
    if trial.leaderboard_channel_id:
        ch_lines.append(f"<#{trial.leaderboard_channel_id}> (leaderboard)")
    embed.add_field(name="Channels", value="\n".join(ch_lines) if ch_lines else "None", inline=True)

    role_lines = []
    if trial.participant_role_id:
        role_lines.append(f"<@&{trial.participant_role_id}> (participant)")
    if trial.finisher_role_id:
        role_lines.append(f"<@&{trial.finisher_role_id}> (finisher)")
    embed.add_field(name="Roles", value="\n".join(role_lines) if role_lines else "None", inline=True)

    cat_name = "None"
    if trial.category_id_id:
        try:
            cat = AsyncRaceCategory.get_by_id(trial.category_id_id)
            cat_name = cat.name
        except Exception:
            cat_name = f"ID {trial.category_id_id}"
    embed.add_field(name="Bot Category", value=cat_name, inline=True)

    view = ArchiveTrialView(trial, discord_server, trial_cache)
    await send_message(interaction, embed=embed, view=view)

########################################################################################################################
class ArchiveTrialView(nextcord.ui.View):
    def __init__(self, trial, discord_server, trial_cache):
        super().__init__(timeout=300)
        self.trial = trial
        self.discord_server = discord_server
        self.trial_cache = trial_cache

    @nextcord.ui.button(label="Category Only", style=nextcord.ButtonStyle.blurple, row=0)
    async def category_only(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self._do_archive(interaction, channels=False, roles=False)
        self.stop()

    @nextcord.ui.button(label="Remove Roles & Category", style=nextcord.ButtonStyle.blurple, row=0)
    async def roles_and_category(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self._do_archive(interaction, channels=False, roles=True)
        self.stop()

    @nextcord.ui.button(label="Remove Channels & Category", style=nextcord.ButtonStyle.blurple, row=1)
    async def channels_and_category(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self._do_archive(interaction, channels=True, roles=False)
        self.stop()

    @nextcord.ui.button(label="Remove All", style=nextcord.ButtonStyle.danger, row=1)
    async def remove_all(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        await self._do_archive(interaction, channels=True, roles=True)
        self.stop()

    async def _do_archive(self, interaction, channels, roles):
        results = []

        if channels:
            channel_ids = [
                (self.trial.spoilers_channel_id, "spoilers"),
                (self.trial.general_channel_id, "general"),
                (self.trial.leaderboard_channel_id, "leaderboard"),
            ]
            for cid, label in channel_ids:
                if cid:
                    try:
                        ch = await self.discord_server.fetch_channel(cid)
                    except nextcord.errors.NotFound:
                        logging.warning(f"Archive trial '{self.trial.display_name}': {label} channel {cid} not found in Discord (already deleted?)")
                        results.append(f"{label.capitalize()} channel not found (already deleted?)")
                        continue
                    except Exception as e:
                        logging.error(f"Archive trial '{self.trial.display_name}': could not fetch {label} channel {cid}: {e}")
                        results.append(f"Warning: could not fetch {label} channel: {e}")
                        continue
                    try:
                        await ch.delete(reason=f"Trial archived: {self.trial.display_name}")
                        results.append(f"{label.capitalize()} channel deleted")
                    except Exception as e:
                        logging.error(f"Archive trial '{self.trial.display_name}': could not delete {label} channel {cid}: {e}")
                        results.append(f"Warning: could not delete {label} channel: {e}")

        if roles:
            for rid, label in [(self.trial.finisher_role_id, "finisher"), (self.trial.participant_role_id, "participant")]:
                if rid:
                    role = self.discord_server.get_role(rid)
                    if role:
                        try:
                            await role.delete(reason=f"Trial archived: {self.trial.display_name}")
                            results.append(f"{label.capitalize()} role deleted")
                        except Exception as e:
                            logging.error(f"Archive trial '{self.trial.display_name}': could not delete {label} role {rid}: {e}")
                            results.append(f"Warning: could not delete {label} role: {e}")
                    else:
                        logging.warning(f"Archive trial '{self.trial.display_name}': {label} role {rid} not found in cache (already deleted?)")
                        results.append(f"{label.capitalize()} role not found (already deleted?)")

        if self.trial.category_id_id:
            try:
                cat = AsyncRaceCategory.get_by_id(self.trial.category_id_id)
                cat.active = False
                cat.save()
                results.append(f"Bot category '{cat.name}' deactivated")
            except Exception as e:
                logging.error(f"Archive trial '{self.trial.display_name}': could not deactivate bot category {self.trial.category_id_id}: {e}")
                results.append(f"Warning: could not deactivate bot category: {e}")
            delete_messages_by_category_id(self.trial.category_id_id)
            results.append("Pinned race messages cleared from DB")

        self.trial.state = TrialState.Archived
        self.trial.save()
        results.append(f"**{self.trial.display_name}** marked as Archived")

        # Defensive — should already be removed by end_trial
        if self.trial.announcement_message_id in self.trial_cache:
            del self.trial_cache[self.trial.announcement_message_id]

        await send_message(interaction, "Archive complete:\n" + "\n".join(f"• {r}" for r in results))