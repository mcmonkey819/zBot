# -*- coding: utf-8 -*-
import asyncio
import copy
from datetime import datetime, date
from enum import Enum
import logging
import math
import nextcord
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
from ui.ui_elements import *
from ui.ui_util import *

DefaultFooter = "For more information use the commands in the Race Management Info embed. When you're done you can dismiss this message or it will dismiss itself after some time."
RaceButtonMenuMsg = """Use the buttons below to manage races for this server. Descriptions of the functions are below. 
Note that some of the functions are only allowed for public (non-assigned) races. 
  Those are:
    "Pin Race Info"
    "Edit Submit Role"
    "Edit Leaderboard Channel"
"""

########################################################################################################################
# Menu Clases
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

########################################################################################################################
class AsyncRaceButton(nextcord.ui.Button):
    def __init__(self, menu_item: MenuItem, payload = None, *, label : str = None, style: ButtonStyle = ButtonStyle.primary, disabled: bool = False, url: str | None = None, emoji: str | Emoji | PartialEmoji | None = None, row: int | None = None) -> None:
        self.menu_item = menu_item
        self.payload = payload
        super().__init__(style=style, label=label, disabled=disabled, custom_id=menu_item.custom_id, url=url, emoji=None if menu_item.label is None else PartialEmoji.from_str(menu_item.label), row=row)

    async def callback(self, interaction: Interaction) -> None:
        return await self.menu_item.func(interaction, self.payload)

########################################################################################################################
class RaceButtonMenu(menus.ButtonMenu):
    def __init__(self, payload: any, menu_item_list: list[MenuItem], *, use_channel: bool = False, title: str = "", description: str = "", footer: str = DefaultFooter, color: int = 0x5865F2) -> None:
        self.menu_item_list = menu_item_list
        self.use_channel = use_channel
        self.title = title
        self.description = description
        self.footer = footer
        self.color = color

        super().__init__(timeout=None)

        for i in menu_item_list:
            button = AsyncRaceButton(i, payload)
            self.add_item(button)
    
    async def send_initial_message(self, ctx, channel):
        # Send embed message with `self` as the view
        embed = nextcord.Embed(title=self.title, description=self.description, color=self.color)
        if self.footer is not None:
            embed.set_footer(text=self.footer)

        for i in self.menu_item_list:
            embed.add_field(name=f"{i.label} - {i.short_description}", value=i.help_text, inline=False)
        
        if self.use_channel:
            return await channel.send("", view=self, embed=embed)
        else:
            await send_message(self.interaction, "", view=self, embed=embed)
            return await self.interaction.original_message()

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
class zRaceListPageSource(menus.ListPageSource):
    def __init__(self, races_list, server_id, per_page: int=4) -> None:
        self.server_id = server_id
        super().__init__(entries=races_list, per_page=per_page)
    
    def format_page(self, menu, races):
        menu.update_buttons(races)
        table_text = get_race_list_table(races, self.server_id)
        return f"```\n{table_text}\n```"

########################################################################################################################
class zRaceListMenuPages(menus.ButtonMenuPages, inherit_buttons=False):
    def __init__(self, source: zRaceListPageSource, *, style=ButtonStyle.secondary, timeout=None) -> None:
        super().__init__(source, style=style, timeout=timeout)
        # Disable buttons that are unavailable
        self._disable_unavailable_buttons()

        self.race_buttons = []
        for i in range(0, source.per_page):
            button = AsyncRaceButton(MenuItem(None, show_race_details, f"race_button_{i}", "Race Info", "View race info for labelled race ID"), 0, label="[RaceID]")
            self.race_buttons.append(button)
            self.add_item(button)

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(AsyncRaceButton(MenuItem('↩️', self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(AsyncRaceButton(MenuItem('⬅️', self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(AsyncRaceButton(MenuItem('➡️', self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(AsyncRaceButton(MenuItem('↪️', self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    def update_buttons(self, races):
        # Update the race buttons
        for i,r in enumerate(races):
            self.race_buttons[i].label = f"{r.id}"
            self.race_buttons[i].payload = r.id
            self.race_buttons[i].disabled = False

        if len(races) < self.source.per_page:
            for i in range(self.source.per_page - (self.source.per_page - len(races)), self.source.per_page):
                self.race_buttons[i].label = "--"
                #self.race_buttons[i].payload = 0
                self.race_buttons[i].disabled = True
        
    async def send_initial_message(self, ctx, channel):
        races = await self.source.get_page(0)
        self.update_buttons(races)

        await send_message(self.interaction, self.source.format_page(self, races), view=self)
        return await self.interaction.original_message()
    
########################################################################################################################
class zCategoryListPageSource(menus.ListPageSource):
    def __init__(self, category_list, server_id, per_page: int=8) -> None:
        self.server_id = server_id
        super().__init__(entries=category_list, per_page=per_page)
    
    def format_page(self, menu, categories):
        table_data = [["ID", "Category Name", "Description"]]
        for c in categories:
            table_data.append([c.id, c.name, c.description])
        return f"```\n{tabulate(table_data, headers="firstrow", tablefmt="double_grid")}\n```"

########################################################################################################################
class zCategoryListMenuPages(menus.ButtonMenuPages, inherit_buttons=False):
    def __init__(self, source: zCategoryListPageSource, *, style=ButtonStyle.secondary, timeout=None) -> None:
        super().__init__(source, style=style, timeout=timeout)
        # Disable buttons that are unavailable
        self._disable_unavailable_buttons()

        # Add the page buttons if there's more than one page
        if self.source.get_max_pages() > 1:
            self.add_item(AsyncRaceButton(MenuItem('↩️', self.go_to_first_page, 'first_page', 'First Page', 'Go to the first page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(AsyncRaceButton(MenuItem('⬅️', self.go_to_previous_page, 'previous_page', 'Previous Page', 'Go to the previous page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(AsyncRaceButton(MenuItem('➡️', self.go_to_next_page, 'next_page', 'Next Page', 'Go to the next page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))
            self.add_item(AsyncRaceButton(MenuItem('↪️', self.go_to_last_page, 'last_page', 'Last Page', 'Go to the last page of the list.', include_interaction=False), None, style=ButtonStyle.primary, row=2))

    async def send_initial_message(self, ctx, channel):
        categories = await self.source.get_page(0)
        await send_message(self.interaction, self.source.format_page(self, categories), view=self)
        return await self.interaction.original_message()

########################################################################################################################
# Category Menu Functions
########################################################################################################################
async def create_edit_category_command(interaction, payload):
    await interaction.response.defer(ephemeral=True, with_message=True)
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
async def create_edit_race(interaction, payload):
    await send_message(interaction, "Soon...")
    pass

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
        # Otherwise delete the category
        name = category.name
        category.delete_instance()
        await send_message(interaction, f"Category {category.name} has been deleted.")

########################################################################################################################
async def category_edit_scoring(interaction, category):
    await interaction.response.defer(ephemeral=True, with_message=True)

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
    await interaction.response.defer(ephemeral=True, with_message=True)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)

    logging.info(f"{interaction.user.display_name} selected submit role: {selected_role} for category {category.id}")
    category.submit_role = selected_role
    category.save()
    await send_message(interaction, "Category Submit Role Saved")

########################################################################################################################
async def category_edit_create_role(interaction, category):
    await interaction.response.defer(ephemeral=True, with_message=True)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)
    logging.info(f"{interaction.user.display_name} selected create role: {selected_role} for category {category.id}")
    category.create_role = selected_role
    category.save()
    await send_message(interaction, "Category Create Role Saved")

########################################################################################################################
async def category_edit_leaderboard_channel(interaction, category):
    await interaction.response.defer(ephemeral=True, with_message=True)

    logging.info(f"category_edit_leaderboard_channel: {category.leaderboard_channel}")

    db_msg = None
    # If there's an existing leaderboard message, ask if the user wants to replace it
    if category.leaderboard_message is not None:
        db_msg = get_race_message(category.leaderboard_message)
        if db_msg is not None:
            if db_msg.message_id is not None:
                msg = await interaction.channel.fetch_message(db_msg.message_id)
                if msg is not None:
                    confirmed = await zConfirmMenu(f"Replace existing leaderboard message with a new one?").prompt(interaction)
                    if not confirmed:
                        await send_message(interaction, "Cancelled")
                        return

    # Prompt for the new desired channel
    selected_channel = await prompt_for_channel(interaction)

    logging.info(f"{interaction.user.display_name} selected leaderboard channel: {selected_channel} for category {category.id}")
    # If there's not already a race message create one now
    if db_msg is None:
        db_msg = AsyncRaceMessage(server_id=category.server_id, channel_id=selected_channel)
    
    if db_msg.message_id is not None:
        # Delete the existing message
        await msg.delete()
        db_msg.message_id = None

    db_msg.save()
    await send_message(interaction, "Category Leaderboard Channel Saved")

    # Finally, post an updated leaderboard in the new leaderboard channel
    await update_category_leaderboard(interaction, category, selected_channel)

########################################################################################################################
async def category_edit_points(interaction, category):
    await interaction.response.defer(ephemeral=True, with_message=True)

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
# Race Menu Functions
########################################################################################################################
async def create_edit_race_command(interaction, payload):
    await interaction.response.defer(ephemeral=True, with_message=True)
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
    await interaction.response.defer(ephemeral=True, with_message=True)

    # We can only delete a race if it's inactive and has no submissions
    has_submissions = race_has_submissions(race.id)
    if has_submissions:
        await send_message(interaction, "Cannot delete this race because it has submissions.") 
        return
    
    if race.state != RaceState.Inactive:
        await send_message(interaction, "Cannot delete this race because it is not inactive.")
        return
    
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
    await send_message(interaction, f"Race {race.id} state changed to {new_state}")

########################################################################################################################
async def race_pin(interaction, race):
    # Ask for the channel to pin the race to
    channel_id = await prompt_for_channel(interaction)
    if channel_id is None:
        await send_message(interaction, "Cancelled")
        return

    # If there's an existing pinned message, ask if the user wants to replace it
    if race.race_info_message is not None and race.race_info_message.message_id is not None and race.race_info_message.message_id != 0:
        confirm = await zConfirmMenu(f"There is an existing race info message pinned in channel ID {race.race_info_message.channel_id}. Replace existing pinned message with a new one?").prompt(interaction)
        if not confirm:
            await send_message(interaction, "Cancelled")
            return

    # Finally pin the race
    succcess = await pin_race_info(channel_id, race, interaction)
    if succcess:
        await send_message(interaction, f"Race #{race.id} pinned to channel ID {channel_id}")
    else:
        await send_message(interaction, f"**ERROR** Failed to pin Race #{race.id} to channel ID {channel_id}")

########################################################################################################################
async def race_edit_submit_role(interaction, race):
    await interaction.response.defer(ephemeral=True, with_message=True)

    # Prompt for the desired role
    selected_role = await prompt_for_role(interaction)
    logging.info(f"{interaction.user.display_name} selected submit role: {selected_role} for race {race.id}")
    race.submission_role = selected_role
    race.save()
    await send_message(interaction, "Submit Role Saved")

########################################################################################################################
async def race_edit_leaderboard_channel(interaction, race):
    await interaction.response.defer(ephemeral=True, with_message=True)

    # Prompt for the desired channel
    selected_channel = await prompt_for_channel(interaction)
    
    logging.info(f"{interaction.user.display_name} selected leaderboard channel: {selected_channel} for race {race.id}")

    if race_has_submissions(race.id):
        await update_race_leaderboard(interaction, race, selected_channel)
    else:
        # If there's no submissions, just save the channel_id
        if race.leaderboard_message is None:
            race.leaderboard_message = AsyncRaceMessage(server_id=race.server_id, channel_id=selected_channel)
        else:
            race.leaderboard_message.channel_id = selected_channel
        race.leaderboard_message.save()
        
    await send_message(interaction, "Category Leaderboard Channel Saved")

########################################################################################################################
async def race_assign_racer(interaction, race):
    # Racers can only be assigned when in the inactive state
    if race.state != RaceState.Inactive:
        await send_message(interaction, "Can only assign racers in the `Inactive` state.")
    
    # Prompt for the user to assign, removing already assigned racers
    user = await zUserSelectView(None).prompt(interaction)
    
    # Create a race assignment for this user
    assignment = AsyncRaceRoster(race_id=race.id, user_id=user.id)
    assignment.save()

    await send_message(interaction, f"User {user.display_name} assigned")
########################################################################################################################
async def race_edit_submission(interaction, race):
    # Get a list of submissions for this race
    submissions = get_sorted_race_submissions(race.id)

    if submissions is None or len(submissions) == 0:
        await send_message(interaction, "No submissions found for this race")
        return

    # Create a select list from the submissions
    select_list = [nextcord.SelectOption(label="Cancel...", value=0, description="Cancel the operation")]
    for s in submissions:
        user = interaction.client.get_user(s.user_id)
        select_list.append(nextcord.SelectOption(label=f"{user.display_name} - {s.finish_time}", value=s.id, description=f"{user.display_name} - {s.finish_time}"))
    
    # Prompt the user to select a submission
    view = zSingleSelectView(select_list, on_select_edit_submission, "Choose Submission To Edit..")
    await send_message(interaction, view=view)

async def on_select_edit_submission(submission_id, interaction):
    if submission_id == 0:
        await send_message(interaction, "Cancelled")
        return
    
    # Get the submission and send the submission edit modal
    submission = get_race_submission_by_id(submission_id)
    if submission is not None:
        # Send the submission edit modal
        submit_handler = zRaceSubmitHandler(submission.race_id, submission)
        await submit_handler.send_submit_modal(interaction)

########################################################################################################################
# Racer Info Menu Functions
########################################################################################################################
async def racer_info_stats(interaction, payload):
    await show_racer_stats(interaction, interaction.user.id)
    pass

########################################################################################################################
async def racer_info_show_open_races(interaction, payload):
    # Get the list of open races
    races = get_open_races(interaction.guild_id)

    # Display it as a paginated list
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id, per_page=4),
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
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id, per_page=4),
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
    category_list_menu = zCategoryListMenuPages(source=zCategoryListPageSource(categories, interaction.guild_id, per_page=8),
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
    race_list_menu = zRaceListMenuPages(source=zRaceListPageSource(races, interaction.guild_id, per_page=4),
                                        style=ButtonStyle.secondary,
                                        timeout=None)
    
    await race_list_menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
# Other Menu Functions
########################################################################################################################
async def send_moderator_menu(interaction, channel):
    title = f"Async Race Moderation"
    description = f"Use the buttons below to manage aync races and categories. Descriptions of the functions are below."
    menu = RaceButtonMenu(None, ModeratorMenuItems, use_channel=True, title=title, description=description)
    await menu.start(interaction=interaction, channel=channel, ephemeral=False)
    return menu.message

########################################################################################################################
async def send_racer_menu(interaction, channel):
    title = f"Async Race Dashboard"
    description = f"Use the buttons below to discover races, view your stats and more."
    menu = RaceButtonMenu(None, RacerInfoButtonMenuItems, use_channel=True, title=title, description=description)
    await menu.start(interaction=interaction, channel=channel, ephemeral=False)
    return menu.message

########################################################################################################################
async def send_category_menu(interaction, category_id):
    category = get_category(category_id)
    if category is None:
        return

    title = f"`{category.name}` Category Management"
    description = f"Use the buttons below to manage the `{category.name}` category.\n `{category.name}` Description: `{category.description}`"
    menu = RaceButtonMenu(category, CategoryButtonMenuItems, use_channel=False, title=title, description=description)
    await menu.start(interaction=interaction, ephemeral=True)

########################################################################################################################
async def send_race_menu(interaction, race_id):
    race = get_race(race_id)
    if race is None:
        logging.info(f"ERROR: Race with ID {race_id} not found")
        return

    title = f"Race Management for Race ID {race.id}"
    description = f"Use the buttons below to manage Race ID {race.id} category.\n Description: `{race.description}`"
    footer = "For more information about race management, use the commands in the Race Management Info embed"
    menu = RaceButtonMenu(race, RaceButtonMenuItems, use_channel=False, title=title, description=description)
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
async def show_racer_stats(interaction, user_id):
    # Stats to show: Number of races, 1st places, podiums, favorite category, recent races (with buttons)
    
    await send_message(interaction, "racer stats coming soon...")

########################################################################################################################
# Menu Static Data
########################################################################################################################
ModeratorMenuItems = [
    MenuItem('🏷️', create_edit_category_command, 'create_edit_category', 'Categories', 'Create a new category or modify an existing category.'),
    MenuItem('🏎️', create_edit_race_command, 'create_edit_race', 'Races', 'Create a new race or modify an existing race.'),
]

CategoryButtonMenuItems = [
    MenuItem('✏️', category_edit_description, 'category_edit_description', 'Edit Description', 'Allows you to edit the name & description of the category.'),
    MenuItem('🗑️', category_delete, 'category_delete', 'Delete Category', 'Deletes the category. This will only succeed if there are no races created that use the category.'),
    MenuItem('📝', category_edit_scoring, 'category_edit_scoring', 'Edit Scoring Method', 'Allows you to choose a scoring method for races in this category. See the "Category Scoring" command under the Race Moderation Info embed for more information on the available methods.'),
    MenuItem('👤', category_edit_submit_role, 'category_edit_submit_role', 'Choose Submit Role', 'Allows you to choose the role that is assigned to users when they submit a time for this category. Choosing the "None" option means no role will be assigned.'),
    MenuItem('🗣️', category_edit_create_role, 'category_edit_create_role', 'Choose Create Ping Role', 'Allows you to select a role to be pinged on race creation for this category. The announcement message will be editable at the time of creation. Choosing the "None" option will result in no new race ping.'),
    MenuItem('🥇', category_edit_leaderboard_channel, 'category_edit_leaderboard_channel', 'Set Leaderboard Channel', 'Allows you to select a channel to display the points leaderboard for this category. The leaderboard will be updated when races are completed. Choosing the "None" option will result in no leaderboard being displayed.'),
    MenuItem('🔢', category_edit_points, 'category_edit_points', 'Modify Racer Point Totals', 'Allows you to manually modify the points of racers in this category. This is useful for manually awarding bonus points or correcting errors.'),
]

RaceButtonMenuItems = [
    MenuItem('✏️', race_edit_core, 'race_edit_core', 'Edit Race', 'Allows you to edit the core info about the race, such as the seed, hash, description and instructions.'),
    MenuItem('🗑️', race_delete, 'race_delete', 'Delete Race', 'Deletes the race. This will only succeed if the race is inactive and there are no submissions for the race.'),
    MenuItem('🚦', race_change_state, 'race_change_state', 'Change Race State', 'Allows you change the race state. Inactive state is used to set up the race. Active state will allow users to discover and submit to the race. Completed state will prevent new submissions and, if applicable, score the race.'),
    MenuItem('📌', race_pin, 'race_pin', 'Pin Race Info', 'Allows you to select a a channel to pin the race info message. The message will include the core race info as well as buttons for submission, forfeit and viewing the leaderboard. Chossing "None" for channel will unpin the race info if it is already pinned.'),
    MenuItem('👤', race_edit_submit_role, 'race_edit_submit_role', 'Choose Submit Role', 'Allows you to choose the role that is assigned to users when they submit a time for this race. This is in addition to any role assigned by the race category. Choosing the "None" option means no role will be assigned.'),
    MenuItem('🥇', race_edit_leaderboard_channel, 'race_edit_leaderboard_channel', 'Set Leaderboard Channel', 'Allows you to select a channel to display the leaderboard for this race. The leaderboard will be updated when times are submitted. Choosing the "None" option will result in no leaderboard being displayed.'),
    MenuItem('🫵🏽', race_assign_racer, 'race_assign_racer', 'Assign Racers', 'Allows you to assign specific racers to this race. See the "Race Assignment" command under the Race Moderation Info embed to learn more about race assignments.'),
    MenuItem('🔧', race_edit_submission, 'race_edit_submission', 'Modify Submission', 'Allows you to modify a submission to this race. This is useful for correcting errors or fixing scoring errors.'),
]

RacerInfoButtonMenuItems = [
    MenuItem('📈', racer_info_stats, 'racer_info_stats', 'View My Stats', 'Displays your race stats.'),
    MenuItem('📖', racer_info_show_open_races, 'racer_info_show_open_races', 'Show Open Races', 'Shows a list of open async races. Selecting a race from the drop down will display additional details and commands.'),
    MenuItem('🫵🏽', racer_info_show_assigned_races, 'racer_info_show_assigned_races', 'Show Races Assigned to Me', 'Shows a list of races that have been assigned to you. Selecting a race from the drop down will display additional details and commands.'),
    MenuItem('🏷️', racer_info_show_categories, 'racer_info_show_categories', 'Show Categories', 'Creates a dropdown menu with a list of categories, selecting a category will display info and additional commands.'),
    MenuItem('👀', racer_info_view_other_racer, 'racer_info_view_other_racer', 'View Another Racer', "Shows a list of racers in the server. Selecting a racer from the drop down will display that racer's stats and a list of their completed races."),
    MenuItem('🏁', racer_info_show_completed_races, 'racer_info_show_completed_races', 'Show Completed Races', 'Shows a list of completed races. Selecting a race from th drop down will display additional information and commands. Note that completed races will not accept new submissions, but the race info and leaderboard can be viewed.'),
]