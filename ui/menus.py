# -*- coding: utf-8 -*-
import asyncio
import copy
from datetime import datetime, date
from enum import Enum
import logging
import math
import nextcord
import random
from nextcord.emoji import Emoji
from nextcord.enums import ButtonStyle
from nextcord.ext import commands, menus
from nextcord.ext.menus.constants import DEFAULT_TIMEOUT
from nextcord.interactions import Interaction
from nextcord.partial_emoji import PartialEmoji
import re
from tabulate import tabulate
tabulate.PRESERVE_WHITESPACE = True

import validators

from db.zBot_db_orm import *
from ui.menus_string_data import *
from ui.ui_elements import *

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
        await menus.Menu.start(self, interaction, wait=True)
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
        menu.update_buttons(races, self.race_emojis)

        embed = nextcord.Embed(color=0x5865F2, title=self.title, description=self.body_text)
        
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

        self.race_buttons = []
        for i in range(0, source.per_page):
            button = zButton(MenuItem(None, show_race_details, f"race_button_{i}", "Race Info", "View race info for labelled race ID"), 0, label="[RaceID]")
            self.race_buttons.append(button)
            self.add_item(button)

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(zButton(MenuItem(FirstPageEmoji, self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(PreviousPageEmoji, self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(NextPageEmoji, self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(LastPageEmoji, self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    def update_buttons(self, races, emojis=None):
        # Update the race buttons
        for i,r in enumerate(races):
            self.race_buttons[i].label = emojis[i] if emojis is not None else f"{r.id}"
            self.race_buttons[i].payload = r.id
            self.race_buttons[i].disabled = False

        if len(races) < self.source.per_page:
            for i in range(self.source.per_page - (self.source.per_page - len(races)), self.source.per_page):
                self.race_buttons[i].label = "--"
                self.race_buttons[i].disabled = True
        
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
        menu.update_buttons(categories, self.category_emojis)

        table_data = [["ID", "Category Name", "Description"]]
        for i, c in enumerate(categories):
            table_data.append([f"{self.category_emojis[i]} - {c.id}", c.name, c.description])
        return f"```\n{tabulate(table_data, headers="firstrow", tablefmt="double_grid")}\n```"

class zCategoryListMenuPages(menus.ButtonMenuPages, inherit_buttons=False):
    def __init__(self, source: zCategoryListPageSource, *, style=ButtonStyle.secondary, timeout=None) -> None:
        super().__init__(source, style=style, timeout=timeout)
        # Disable buttons that are unavailable
        self._disable_unavailable_buttons()
        self.category_buttons = []
        for i in range(0, source.per_page):
            button = zButton(MenuItem(None, show_category_leaderboard, f"category_button_{i}", "Category Leaderboard", "View leaderboard for category"), 0, label="[CategoryID]")
            self.category_buttons.append(button)
            self.add_item(button)

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(zButton(MenuItem(FirstPageEmoji, self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(PreviousPageEmoji, self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(NextPageEmoji, self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(LastPageEmoji, self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    def update_buttons(self, categories, emojis=None):
        # Update the category leaderboard buttons
        for i,c in enumerate(categories):
            self.category_buttons[i].label = emojis[i] if emojis is not None else f"{c.id}"
            self.category_buttons[i].payload = c.id
            self.category_buttons[i].disabled = False

        if len(categories) < self.source.per_page:
            for i in range(self.source.per_page - (self.source.per_page - len(categories)), self.source.per_page):
                self.category_buttons[i].label = "--"
                self.category_buttons[i].disabled = True

    async def send_initial_message(self, ctx, channel):
        categories = await self.source.get_page(0)
        
        await send_message(self.interaction, self.source.format_page(self, categories), view=self)
        return await self.interaction.original_message()
    
########################################################################################################################
class zRaceLeaderboardPageSource(menus.ListPageSource):
    def __init__(self, submission_list, server_id, bot_client, *, per_page: int=10, title=None, body_text=None) -> None:
        self.server_id = server_id
        self.bot_client = bot_client
        self.title = title
        self.body_text = body_text
        self.place_emojis = get_emoji_list()

        super().__init__(entries=submission_list, per_page=per_page)

    async def format_page(self, menu, submissions):
        menu.update_buttons(submissions, self.place_emojis)
        return await get_race_leaderboard_embed(self.title, self.body_text, submissions, menu.current_page, self.per_page, self.bot_client, self.place_emojis)

class zRaceLeaderboardMenuPages(menus.ButtonMenuPages, inherit_buttons=False):
    def __init__(self, source: zRaceLeaderboardPageSource, *, style=ButtonStyle.secondary, timeout=None) -> None:
        super().__init__(source, style=style, timeout=timeout)
        
        # Disable buttons that are unavailable
        self._disable_unavailable_buttons()

        self.submission_buttons = []
        for i in range(0, source.per_page):
            button = zButton(MenuItem(None, show_submission_details, f"submission_button_{i}", "Submission Details", "View details for the submission"), 0, label="[SubmissionID]")
            self.submission_buttons.append(button)
            self.add_item(button)

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(zButton(MenuItem(FirstPageEmoji, self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(PreviousPageEmoji, self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(NextPageEmoji, self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(zButton(MenuItem(LastPageEmoji, self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    def update_buttons(self, submissions, emojis=None):
        # Update the submission buttons
        for i,s in enumerate(submissions):
            self.submission_buttons[i].label = emojis[i] if emojis is not None else f"{s.id}"
            self.submission_buttons[i].custom_id = str(s.id)
            self.submission_buttons[i].payload = s.id
            self.submission_buttons[i].disabled = False

        if len(submissions) < self.source.per_page:
            for i in range(self.source.per_page - (self.source.per_page - len(submissions)), self.source.per_page):
                self.race_buttons[i].label = "--"
                self.race_buttons[i].disabled = True
        
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

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='⏱️ Submit/Edit Time')
    async def submit_time_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Lookup if the user has a submission for this race already
        submission = get_race_submission(interaction.user.id, self.race_id)
        submit_handler = zRaceSubmitHandler(self.race_id, submission)
        await submit_handler.send_submit_modal(interaction)

    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='🏳️ Forfeit Race')
    async def forfeit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Check if the user has already submitted a time for this race
        if get_race_submission(interaction.user.id, self.race_id) is not None:
            await send_message(interaction, "Time already submitted for this race, use `Submit/Edit` button to edit")
            return
        else:
            forfeit_race(interaction.user.id, self.race_id)

    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='🥇 Leaderboard')
    async def leaderboard_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await show_race_leaderboard(interaction, self.race_id)

########################################################################################################################
# Category Menu Functions
########################################################################################################################
async def create_edit_category_command(interaction, payload):
    await defer(interaction)
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

    select_list = copy.deepcopy(PointsType.SelectOptionList)
    if category.points_type is None:
        select_list[0].default = True
    for s in select_list:
        if s.value == category.points_type:
            s.default = True
            break
    
    selected = await zSingleSelectView(select_list, None, "Choose Scoring Method...").prompt(interaction)
    
    category.points_type = selected if selected != 0 else None
    category.save()

    await send_message(interaction, f"Category Scoring Method Saved")

########################################################################################################################
async def category_edit_submit_role(interaction, category):
    await defer(interaction)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)

    logging.info(f"{interaction.user.display_name} selected submit role: {selected_role} for category {category.id}")
    category.submit_role = selected_role
    category.save()
    await send_message(interaction, "Category Submit Role Saved")

########################################################################################################################
async def category_edit_create_role(interaction, category):
    await defer(interaction)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)
    logging.info(f"{interaction.user.display_name} selected create role: {selected_role} for category {category.id}")
    category.create_role = selected_role
    category.save()
    await send_message(interaction, "Category Create Role Saved")

########################################################################################################################
async def category_edit_leaderboard_channel(interaction, category):
    await defer(interaction)

    logging.info(f"category_edit_leaderboard_channel")

    # Prompt for the new desired channel
    selected_channel = await prompt_for_channel(interaction)

    logging.info(f"{interaction.user.display_name} selected leaderboard channel: {selected_channel} for category {category.id}")
    
    # Post an updated leaderboard in the new leaderboard channel
    channel = interaction.guild.get_channel(selected_channel)
    if channel is not None:
        await post_channel_category_leaderboard(interaction, channel, category.id, interaction.client)
        await send_message(interaction, "Category Leaderboard Updated")
    else:
        await send_message(interaction, "**ERROR** Could not fetch selected channel. Please contact a bot admin.")

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
        select_list.append(nextcord.SelectOption(label=f"{member.display_name} - {p.points}", value=p.id, description=f"{member.display_name} Current Points: {p.points}"))

    view = zSingleSelectView(select_list, category_edit_db_points, "Choose Racer To Modify...")
    await send_message(interaction, view=view)

async def category_edit_db_points(points_id, interaction):
    db_points = get_category_points_by_id(points_id)
    server = get_server_from_interaction(interaction)
    if db_points is not None:
        # Ask what the new points value should be
        member = await server.fetch_member(db_points.user_id)
        new_points = await prompt_for_value(interaction,
                                            f"Enter New Points for `{member.display_name}`",
                                            "Points",
                                            str(db_points.points))
        # Update the points value
        logging.info(f"{interaction.user.display_name} changed points for {member.display_name} from {db_points.points} to {new_points}")
        db_points.points = int(new_points)
        db_points.save()
        await send_message(interaction, f"Points for {member.display_name} updated to {new_points}")

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
async def category_misc_toggles(interaction, category):
    # Build the list of toggle fields
    toggle_list = []
    toggle_list.append(get_ping_assigned_field(category))
    toggle_list.append(get_remove_category_leaderboard_field(category))
    toggle_list.append(get_leaderboard_type_toggle_field(category))
    toggle_list.append(get_category_active_toggle_field(category))

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
        emoji=ChangeStateEmoji,
        embed_field=EmbedField(name=f"{ChangeStateEmoji} - Category Visibility",
                               value=active_field_to_str(category.active),
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
    # Get a list of races
    select_list = get_race_select_list(interaction.guild_id)
    
    # Add the option for creating a new category to the front of the list
    select_list.insert(0, nextcord.SelectOption(label="Create New...", value=0, description="Create a new race."))
    
    # Prompt the user to select an option
    view = zSingleSelectView(select_list, create_edit_race, "Choose Race..")
    await send_message(interaction, view=view)

async def create_edit_race(race_id, interaction):
    if race_id == 0 or race_id is None:
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
    await send_message(interaction, "Race ID {race_id} has been deleted.")

########################################################################################################################
async def race_change_state(interaction, race):
    # Query for the new race state
    select_list = copy.deepcopy(RaceState.SelectOptionList)
    for s in select_list:
        if s.value == race.state:
            s.default = True
            break

    new_state = await zSingleSelectView(select_list, None, "Choose new state...").prompt(interaction)

    # Do some sanity checks of the new state
    if new_state == RaceState.Inactive:
        # If the new state is inactive, make sure there are no submissions
        if race_has_submissions(race.id):
            await send_message(interaction, "Cannot change state to Inactive because there are submissions.")
            return
    elif new_state == RaceState.Active:
        if race.state == RaceState.Completed:
            # For categories that have points, we can't go from completed to active
            if race.category.points_type != PointsType.NoScoring:
                await send_message(interaction, "Cannot change state to Active because the race has already been scored.")
                return
    elif new_state == RaceState.Completed:
        # If there are no submissions, confirm that the user meant to select `Completed`` and not `Inactive`
        if race_has_submissions(race.id) == False:
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
                confirmed = await zConfirmMenu("Not all assigned racers have submitted, do you want to change to 'Completed' anyway?").prompt(interaction)
                if not confirmed:
                    await send_message(interaction, "Cancelled")
                    return
    # Now that all checks are done, save the new race state
    race.state = new_state
    race.save()
    
    if new_state == RaceState.Completed:
        # If the new state is completed, score the race
        score_race(race)

        # Then update the category and/or race leaderboards
        await update_category_leaderboard(interaction, race)
        await update_race_leaderboard(interaction, race)
    
    await send_message(interaction, f"Race {race.id} state changed to {new_state}")

########################################################################################################################
async def race_pin(interaction, race):
    # Ask for the channel to pin the race to
    channel_id = await prompt_for_channel(interaction)
    if channel_id is None:
        await send_message(interaction, "Cancelled")
        return

    # Delete any existing race info messages
    msg_list = get_messages_by_race_id(race.id, RaceMessageType.RaceInfo)
    if msg_list is not None:
        for m in msg_list:
            if m.message_id is not None:
                await delete_message(get_server_from_interaction(interaction), m.id)

    # Then post the new race info message
    succcess = await pin_race_info(channel_id, race, interaction)
    if succcess:
        await send_message(interaction, f"Race #{race.id} pinned to channel ID {channel_id}")
    else:
        await send_message(interaction, f"**ERROR** Failed to pin Race #{race.id} to channel ID {channel_id}")

########################################################################################################################
async def race_edit_submit_role(interaction, race):
    await defer(interaction)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)
    logging.info(f"{interaction.user.display_name} selected submit role: {selected_role} for race {race.id}")
    race.submission_role = selected_role
    race.save()
    await send_message(interaction, "Submit Role Saved")

########################################################################################################################
async def race_assign_racer(interaction, race):
    # Racers can only be assigned when in the inactive state
    if race.state != RaceState.Inactive:
        await send_message(interaction, "Can only assign racers in the `Inactive` state.")
    
    # Prompt for the user to assign, removing already assigned racers
    user = await zUserSelectView(None).prompt(interaction)
    
    # Create a race assignment for this user
    assign_racer(user_id=user.id, race_id=race.id)

    await send_message(interaction, f"User {user.display_name} assigned")
########################################################################################################################
async def race_edit_submission(interaction, race):
    # Get a list of submissions for this race
    submissions = get_sorted_race_submissions(race.id)

    if submissions is None or len(submissions) == 0:
        await send_message(interaction, "No submissions found for this race")
        return

    # Create a select list from the submissions
    select_list = [nextcord.SelectOption(label="Create New...", value=-1, description="Create a new submission"),
                   nextcord.SelectOption(label="Cancel...", value=0, description="Cancel the operation")]
    for s in submissions:
        user = await interaction.client.fetch_user(s.user_id)
        select_list.append(nextcord.SelectOption(label=f"{user.display_name} - {s.finish_time}", value=s.id, description=f"{user.display_name} - {s.finish_time}"))
    
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
    
    # Check if the selected user already has a submission to avoid duplicates
    submission = get_race_submission(user.id, race_id)
    
    submit_handler = zRaceSubmitHandler(race_id, submission, include_points=True, user_id=user.id)
    await submit_handler.send_submit_modal(interaction)
    pass

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
    # Get the list of open races
    races = get_open_races(interaction.guild_id)

    # Display it as a paginated list
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id, use_inline_fields=True),
                                        style=ButtonStyle.secondary,
                                        timeout=None)
    
    await race_list_menu.start(interaction=interaction, ephemeral=True)


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
async def prompt_for_role(interaction):
    server = get_server_from_interaction(interaction)
    role_list = get_role_select_list(server)
    
    selected_role = await zSingleSelectView(role_list, None, "Choose Role...").prompt(interaction)
    
    return None if selected_role == 0 else selected_role

########################################################################################################################
async def prompt_for_channel(interaction):
    server = get_server_from_interaction(interaction)
    channel_list = await get_permitted_channel_select_list(interaction.client.user.id, server)
    
    selected_channel = await zSingleSelectView(channel_list, None, "Choose Channel...").prompt(interaction)
    
    return None if selected_channel == 0 else selected_channel

########################################################################################################################
async def show_race_details(interaction, race_id):
    race = get_race(race_id)
    if race is None:
        await send_message(interaction, "**ERROR** Could not find race data. Please notify a bot admin")
        return
    msg_text, seed_embed = get_race_info_message(race)
    await send_message(interaction, msg_text, view=zRaceInfoButtonView(race.id), embed=seed_embed)

########################################################################################################################
async def show_submission_details(interaction, submission_id):
    submission = get_race_submission_by_id(submission_id)
    race_id = submission.race_id.id
    user = await interaction.client.fetch_user(submission.user_id)
    title=f"{user.display_name} Submission for Race ID #{race_id}"
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
        embed.add_field(name="Points", value=str(submission.points), inline=False)
    
    # Get extra info types assigned to this race
    extra_info_assignments = AsyncRaceExtraInfoAssignment.select().where(AsyncRaceExtraInfoAssignment.race_id == race_id)
    logging.info("--: Getting Extra Info Assignments")
    for a in extra_info_assignments:
        # Lookup the extra infos for this submission and add them to the table
        info = get_extra_info(s, a.info_type_id)
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
    user_name = None if user is None else user.display_name
    
    # Collect the core stats
    races = get_completed_races(user_id, interaction.guild_id)
    total_races = len(races)
    total_wins = 0
    total_podiums = 0
    cat_count = dict()
    for r in races:
        submissions = get_sorted_race_submissions(r.id)
        if submissions[0].user_id == user_id:
            total_wins += 1
            total_podiums += 1
        elif submissions[1].user_id == user_id or submissions[2].user_id == user_id:
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
    one_v_one_label = "1v1 Record" if viewing_self else f"{interaction.user.display_name} 1v1 Record vs {user_name}"
    one_v_one_value = f"{one_v_one_wins} - {one_v_one_losses} - {one_v_one_ties}"

    # Store the stats as embed fields
    static_embed_fields = [
        EmbedField("---------------------------------", "**Core Stats**"),
        EmbedField("Total Races", str(total_races), inline=True),
        EmbedField("Race Wins", str(total_wins),inline=True),
        EmbedField("Podium Finishes", str(total_podiums),inline=True),
        EmbedField("Most Raced Category", most_raced_category, inline=True),
        EmbedField(one_v_one_label, one_v_one_value, inline=False),
        EmbedField("---------------------------------", "**Recent Races**")]
    
    # Display the core stats and recent races as a paginated list
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id, use_inline_fields=False, static_embed_fields=static_embed_fields, title=user_name, user_id=user_id),
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
    num_pages = math.ceil(len(submissions) / per_page)
    race_id = submissions[0].race_id
    
    menu_list = []
    for p in range(0, num_pages):
        slice = submissions[p*per_page:(p+1)*per_page]
        emoji_slice = emojis[p*per_page:(p+1)*per_page]
        title = get_race_leaderboard_title(race_id)
        body_text = get_race_leaderboard_description(race_id)
        embed = await get_race_leaderboard_embed(title, body_text, slice, p, per_page, bot_client, emojis=emoji_slice)
        # Create the menu item list
        menu_items = []
        for s in slice:
            menu_items.append(MenuItem(emoji_slice[slice.index(s)], show_submission_details, str(s.id), f"Show Submission {s.id} Details", SubmissionDetailsHelpText))
        submission_id_list = [s.id for s in slice]
        menu = zButtonMenu(submission_id_list, menu_items, embed=embed, use_channel=True)
        menu_list.append(menu)
    
    for menu in menu_list:
        await menu.start(interaction=interaction, channel=channel)
        await menu.message.pin()
        if save_as_category_message:
            race = get_race(race_id)
            save_message(interaction.guild_id, channel.id, menu.message.id, category_id=race.category_id.id)
        else:
            save_message(interaction.guild_id, channel.id, menu.message.id, race_id=race_id)

########################################################################################################################
async def race_edit_leaderboard_channel(interaction, race):
    await defer(interaction)

    # Prompt for the desired channel
    selected_channel = await prompt_for_channel(interaction)
    
    logging.info(f"{interaction.user.display_name} selected leaderboard channel: {selected_channel} for race {race.id}")

    # Find any existing leaderboard message and remove it
    found_existing = False
    leaderboard_msg_list = get_messages_by_race_id(race.id)
    if leaderboard_msg_list is not None and len(leaderboard_msg_list) > 0:
        for m in leaderboard_msg_list:
            if m.message_id is not None:
                found_existing = True
                await delete_message(get_server_from_interaction(interaction), m.id)
    
    message_id = None
    if found_existing:
        # post the leaderboard to the new channel will save the message ID(s) to the DB
        await post_channel_race_leaderboard(interaction, selected_channel, race.id, interaction.client, get_emoji_list())
    else:
        # If there's no existing leaderboard message (because the race hasn't started yet), we just save the channel and race ID
        msg = AsyncRaceMessage(server_id=race.server_id, channel_id=selected_channel, message_id=message_id, race_id=race.id)
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
        races = get_completed_races_by_category(category_id)
        if len(races) == 0:
            await send_message(interaction, f"No completed races yet for category {category.name}")
        else:    
            await post_channel_race_leaderboard(interaction, channel, races[0].id, bot_client, get_emoji_list())
    else:
        embed_list = await get_category_leaderboard_embed_list(category_id, per_page, bot_client)
        #if embed_list is None or len(embed_list) == 0:
        #    await send_message(interaction, f"No points yet for category {category.name}")
        #else:
        for e in embed_list:
            msg = await channel.send(embed=e)
            await msg.pin()
            save_message(interaction.guild_id, channel.id, msg.id)

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

    # Get a list of active race assignments in this category
    assignments = get_active_category_assignments(category.id)

    msg = ""
    for a in assignments:
        user = await interaction.client.fetch_user(a.user_id)
        msg += f"{user.mention} "
    
    msg += f" You have been assigned to a new {category.name} race. Good luck!"
    await interaction.channel.send(msg)

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

    if msgs is None or len(msgs) == 0:
        return
    
    # Extract the channel_id from the message and fetch the channel
    channel = await interaction.guild.get_channel(msgs[0].channel_id)

    # Delete the existing messages
    for m in msgs:
        await delete_message(interaction.guild, m.message_id)

    # Post the updated leaderboard to the channel
    post_channel_category_leaderboard(interaction, channel, race.category_id.id, interaction.client)

########################################################################################################################
async def update_race_leaderboard(interaction, race):
    # Check if there are any category leaderboard messages
    msgs = get_messages_by_race_id(race.id)
    msgs = list(filter(lambda x: x.message_type is RaceMessageType.Leaderboard, msgs))

    if msgs is None or len(msgs) == 0:
        return
    
    # Extract the channel_id from the message and fetch the channel
    channel = await interaction.guild.get_channel(msgs[0].channel_id)

    # Delete the existing messages
    for m in msgs:
        await delete_message(interaction.guild, m.message_id)

    # Post the updated leaderboard to the channel
    post_channel_race_leaderboard(interaction, channel, race.id, interaction.client, get_emoji_list())

########################################################################################################################
def get_emoji_list():
    return random.shuffle(copy(EmojiList))

########################################################################################################################
def get_random_emoji():
    return random.choice(EmojiList)

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
    MenuItem(ToggleEmoji     , category_misc_toggles            , 'category_misc_toggles'            , 'Misc Category Config'     , CategoryMiscToggleDescription),
]

RaceButtonMenuItems = [
    MenuItem(EditEmoji          , race_edit_core               , 'race_edit_core'               , 'Edit Race'              , RaceEditDescription),
    MenuItem(DeleteEmoji        , race_delete                  , 'race_delete'                  , 'Delete Race'            , RaceDeleteDescription),
    MenuItem(ChangeStateEmoji   , race_change_state            , 'race_change_state'            , 'Change Race State'      , RaceChangeStateDescription),
    MenuItem(PinEmoji           , race_pin                     , 'race_pin'                     , 'Pin Race Info'          , RacePinDescription),
    MenuItem(SubmitRoleEmoji    , race_edit_submit_role        , 'race_edit_submit_role'        , 'Choose Submit Role'     , RaceEditSubmitRoleDescription),
    MenuItem(LeaderboardEmoji   , race_edit_leaderboard_channel, 'race_edit_leaderboard_channel', 'Set Leaderboard Channel', RaceEditLeaderboardChannelDescription),
    MenuItem(AssignEmoji        , race_assign_racer            , 'race_assign_racer'            , 'Assign Racers'          , RaceAssignRacerDescription),
    MenuItem(EditSubmissionEmoji, race_edit_submission         , 'race_edit_submission'         , 'Modify Submission'      , RaceEditSubmissionDescription),
    MenuItem(ToggleEmoji        , race_misc_toggles            , 'race_misc_toggles'            , 'Misc Race Config'       , RaceMiscToggleDescription),
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
    MenuItem(ViewOtherEmoji     , racer_info_view_other_racer    , 'racer_info_view_other_racer'    , 'View Another Racer'  , RacerViewOtherRacerDescription),
    MenuItem(HelpEmoji          , show_racer_info_help           , 'show_racer_info_help'           , 'Racer Command Help'  , RacerHelpDescription),
]