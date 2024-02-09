# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, date
import logging
from typing import Optional, Union
from nextcord.emoji import Emoji
from nextcord.enums import ButtonStyle
from nextcord.ext import commands, menus
import nextcord
import re

from nextcord.ext.menus.constants import DEFAULT_TIMEOUT
from nextcord.interactions import Interaction
from nextcord.partial_emoji import PartialEmoji

from db.zBot_db_orm import *
from db.db_util import *
from ui.ui_util import *

########################################################################################################################
# Category Moderation
########################################################################################################################
# Modal which has fields required to create/edit a category
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
        except:
            await send_message(interaction, f"FAILED to save category {self.category.name}")

########################################################################################################################
# View which contains server admin buttons
class zServerAdminView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='✏️ Edit Mod Role')
    async def edit_mod_role_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_admin(interaction) == False:
            return

        server = get_server_from_interaction(interaction)
        role_list = get_role_select_list(server)
        await send_message(interaction, view=zSingleSelectView(role_list,
                                                               self.on_mod_role_select,
                                                               "Choose Role..."))

    ####################################################################################################################
    async def on_mod_role_select(self, role_id, interaction):
        db_server = get_server(interaction.guild_id)
        if db_server is not None:
            db_server.mod_role_id = role_id
            db_server.save()
            await send_message(interaction, "Saved Race Moderator Role")
        else:
            await send_message(interaction, "An error occurred, please contact a bot admin")

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='️📢 Set Announcements Channel')
    async def set_announcements_channel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_admin(interaction) == False:
            return

        server = get_server_from_interaction(interaction)
        channel_list = await get_permitted_channel_select_list(interaction.client.user.id, server)
        await send_message(interaction, view=zSingleSelectView(channel_list,
                                                               self.on_announcements_channel_select,
                                                               "Choose Channel..."))

    ####################################################################################################################
    async def on_announcements_channel_select(self, channel_id, interaction):
        db_server = get_server(interaction.guild_id)
        if db_server is not None:
            db_server.announcement_channel_id = channel_id
            db_server.save()
            await send_message(interaction, "Saved Announcements Channel")
        else:
            await send_message(interaction, "An error occurred, please contact a bot admin")


########################################################################################################################
# View which contains category moderation buttons
class zCategoryModView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➕ Add Category')
    async def add_category_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_mod(interaction) == False:
            return

        # Create and send Add Category modal
        await interaction.response.send_modal(zCategoryAddEditModal(None))

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='✏️ Edit Category')
    async def edit_category_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_mod(interaction) == False:
            return

        # Get the list of categories for this server
        select_list = get_category_select_list(interaction.guild_id)

        if len(select_list) == 0:
            await send_message(interaction, "No categories defined for this server")
            return

        # Create and send category Select view, calling the category select handler
        self.cat_select = zSingleSelectView(select_list, self.on_category_select, "Select a Category")
        await send_message(interaction, view=self.cat_select)

    async def on_category_select(self, category_id, interaction):
        # Create and send Edit Category modal
        category = get_category(category_id)
        await interaction.response.send_modal(zCategoryAddEditModal(category))

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➕ Add Submit Info Type')
    async def add_submit_info_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_mod(interaction) == False:
            return

        # Create and send Add Category modal
        await interaction.response.send_modal(zExtraInfoTypeAddEditModal(None))

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='👉🏾 Assign Extra Info')
    async def assign_extra_info_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_mod(interaction) == False:
            return

        # Prompt to select from list of extra info types
        select_view = zSingleSelectView(get_extra_info_type_select_list(interaction.guild.id),
                                        self.on_info_type_select,
                                        "Select info type to assign...")
        await send_message(interaction, view=select_view)

    async def on_info_type_select(self, info_type_choice, interaction):
        self.info_type_choice = info_type_choice
        # Prompt for what to assign to: server or category
        self.server_choice_id = 1
        self.cat_choice_id = 2
        select_list = [
            nextcord.SelectOption(label="Server", value=self.server_choice_id, description="Assign extra info to be set by default for this server"),
            nextcord.SelectOption(label="Category", value=self.cat_choice_id, description="Assign extra info to be set by default for a race category"),
            ]
        select_view = zSingleSelectView(select_list, self.on_assign_type_select, "Select what to assign to...")
        await send_message(interaction, view=select_view)

    async def on_assign_type_select(self, assign_choice, interaction):
        if assign_choice == self.server_choice_id:
            # Check to see if this assignment has already been made
            if check_server_assignment_exists(self.info_type_choice, interaction.guild.id):
                await send_message(interaction, "Assignment already exists")
                return
            # Then create a new DB assignment with the selected info
            assignment = AsyncRaceExtraInfoAssignment()
            assignment.info_type_id = self.info_type_choice
            assignment.server_id = interaction.guild.id
            assignment.save()
            await send_message(interaction, "Assignment saved")
        else:
            # Send a select to prompt for which category to assign to
            cat_select_view = zSingleSelectView(get_category_select_list(interaction.guild.id),
                                                self.on_cat_assign_select,
                                                "Select Category...")
            await send_message(interaction, view=cat_select_view)

    async def on_cat_assign_select(self, category_id, interaction):
        category_id = category_id
        # Check to see if this assignment has already been made
        if check_category_assignment_exists(self.info_type_choice, category_id):
                await send_message(interaction, "Assignment already exists")
                return
        # Then create a new DB assignment with the selected info
        assignment = AsyncRaceExtraInfoAssignment()
        assignment.info_type_id = self.info_type_choice
        assignment.category_id = category_id
        assignment.save()
        await send_message(interaction, "Assignment saved")

########################################################################################################################
# Modal which has fields required to create/edit an extra info type
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
# Race Moderation
########################################################################################################################
# Modal which has fields required to create/edit a race.
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

        msg = f"Saved Race Info:\n"
        for c in modal.children:
            match c.custom_id:
                case self.seed_id:
                    self.race.seed = c.value
                    msg += "  Seed: "
                case self.hash_id:
                    if c.value is not None:
                        self.race.hash = c.value
                    msg += "  Hash: "
                case self.description_id:
                    self.race.description = c.value
                    msg += "  Description: "
                case self.extra_info_id:
                    if c.value is not None:
                        self.race.additional_instructions = c.value
                    msg += "  Extra Info: "
                case _:
                    continue
            msg += f"{c.value}\n"
        msg += f"  Category ID: {self.category_id}"
        logging.info(msg)

        self.race.save()

        if race_is_new:
            # Create default extra info assignments based on server and category
            server_infos = AsyncRaceExtraInfoAssignment.select().where(
                AsyncRaceExtraInfoAssignment.server_id == self.server_id or
                AsyncRaceExtraInfoAssignment.server_id == AsyncRaceExtraInfoServerAny)
            for s in server_infos:
                a = AsyncRaceExtraInfoAssignment()
                a.info_type_id = s.info_type_id
                a.race_id = self.race.id
                a.save()
            cat_infos = AsyncRaceExtraInfoAssignment.select().where(
                AsyncRaceExtraInfoAssignment.category_id == self.category_id)
            for c in cat_infos:
                a = AsyncRaceExtraInfoAssignment()
                a.info_type_id = c.info_type_id
                a.race_id = self.race.id
                a.save()

        await send_message(interaction, "Race Info Saved")

########################################################################################################################
# Race Mod buttons: Edit Race Info, Edit Category/Role/Leaderboard Channel, Change Race State, Pin Race Info
# View which contains race moderation buttons
class zRaceModView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➕ Add Race')
    async def add_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_mod(interaction) == False:
            return

        # Prompt the user to select a category for the race, then send the add race modal
        await send_message(interaction, view=zSingleSelectView(get_category_select_list(interaction.guild_id),
                                                               self.send_race_modal,
                                                               "Select Race Category"))

    #################################################################################################################
    async def send_race_modal(self, category_id, interaction):
        await interaction.response.send_modal(zRaceAddEditModal(interaction.guild_id, category_id, None))

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='️️️️✏️ Manage Race')
    async def edit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if await check_user_is_mod(interaction) == False:
            return

        race_list = get_race_select_list(interaction.guild_id)
        if len(race_list) == 0:
            await send_message(interaction, "There are no races currently created")
        else:
            race_select_view = zSingleSelectView(
                get_race_select_list(interaction.guild_id),
                self.on_race_select,
                "Choose Race to Manage...")
            await send_message(interaction, view=race_select_view)

    #################################################################################################################
    async def on_race_select(self, race_id, interaction):
        try:
            self.race = AsyncRace.select().where(AsyncRace.id == race_id).get()
        except:
            self.race = None

        if self.race is None:
            err_msg = "ERROR: Race not found in DB"
            logging.info(err_msg)
            await send_message(interaction, err_msg)
            return

        # Check if the race is already pinned
        if self.race.race_info_message is not None:
            pin_label = "Unpin Race Info"
            pin_desc = "Remove the message with race info and buttons for submit actions"
        else:
            pin_label = "Pin Race Info"
            pin_desc = "Create a message with race info and buttons for submit actions"

        self.edit_state_id = 0
        self.pin_race_info_id = 1
        self.set_leaderboard_channel_id = 2
        self.set_submit_role_id = 3
        self.assign_racers_id = 4
        self.edit_info_id = 5
        self.edit_extra_info_id = 6

        edit_select_list = [
                nextcord.SelectOption(label="Change Race State",       value=self.edit_state_id, description="Change the race state"),
                nextcord.SelectOption(label=pin_label,                 value=self.pin_race_info_id, description=pin_desc),
                nextcord.SelectOption(label="Set Leaderboard Channel", value=self.set_leaderboard_channel_id, description="Set a channel to display the race leaderboard in"),
                nextcord.SelectOption(label="Set Submit Role",         value=self.set_submit_role_id, description="Choose a role to be assigned when a racer submits a time for this race"),
        ]

        # Only allow edit of race info or extra info if there are NO submissions
        self.race_has_submissions = race_has_submissions(race_id)
        if self.race_has_submissions:
            # Only allow assigning racers if the race is inactive and there are no submissions
            if self.race.state == RaceState.Inactive:
                edit_select_list.append(nextcord.SelectOption(label="Assign Racers",  value=self.assign_racers_id, description="Assign specific racers to this race"))
            edit_select_list.append(nextcord.SelectOption(label="Edit Race Info",  value=self.edit_info_id, description="Edit the seed, hash or description"))
            edit_select_list.append(nextcord.SelectOption(label="Edit Extra Info", value=self.edit_extra_info_id, description="Edit what extra info will be stored on submissions"))

        edit_select_view = zSingleSelectView(edit_select_list, self.on_edit_select, "Choose Action...")
        await send_message(interaction, view=edit_select_view)

    #################################################################################################################
    async def on_edit_select(self, edit_choice, interaction):
        server = interaction.client.get_guild(interaction.guild_id)
        match edit_choice:
            case self.edit_info_id:
                logging.info("  Edit Race Selected")
                await self.send_race_modal(self.race, self.race.category_id, interaction)
            case self.edit_state_id:
                logging.info("  Change Race State Selected")
                await self.update_race_state(interaction)
            case self.edit_extra_info_id:
                logging.info("  Edit Race Extra Info Selected")
                info_list = get_extra_info_type_select_list(interaction.guild.id, self.race)
                if len(info_list) > 0:
                    await send_message(interaction, view=zMultiSelectView(info_list,
                                                                          len(info_list),
                                                                          self.on_race_extra_info_select,
                                                                          "Choose Info(s)..."))
                else:
                    await send_message(interaction, "No extra info types defined for this server")
            case self.pin_race_info_id:
                logging.info("  Pin/Unpin Race Info Selected")
                if self.race.race_info_message is None:
                    channel_list = await get_permitted_channel_select_list(interaction.client.user.id, server)
                    await send_message(interaction, view=zSingleSelectView(channel_list,
                                                                           self.on_race_info_channel_select,
                                                                           "Choose Channel..."))
                else:
                    await unpin_race(self.race.id, interaction)
            case self.set_leaderboard_channel_id:
                logging.info("  Set Leaderboard Channel Selected")
                channel_list = await get_permitted_channel_select_list(interaction.client.user.id, server)
                await send_message(interaction, view=zSingleSelectView(channel_list,
                                                                       self.on_leaderboard_channel_select,
                                                                       "Choose Channel..."))
            case self.set_submit_role_id:
                logging.info("  Set Race Role Selected")
                role_list = get_role_select_list(server)
                await send_message(interaction, view=zSingleSelectView(role_list,
                                                                       self.on_race_role_select,
                                                                       "Choose Role..."))
            case self.assign_racers_id:
                logging.info("  Assign Racers Selected")
                await self.select_racer(interaction)
            case _:
                logging.info("  Unknown Edit Choice")

    #################################################################################################################
    async def update_race_state(self, interaction):
        # Send race state select
        select_list = RaceState.SelectOptionList.copy()
        for s in select_list:
            if s.value == self.race.state:
                s.default = True
        race_state_select_view = zSingleSelectView(select_list, self.on_race_state_select, "Choose New Race State...")
        await send_message(interaction, view=race_state_select_view)

    #################################################################################################################
    async def on_race_state_select(self, race_state, interaction):
        logging.info(f"Selected state: {race_state}")
        if race_state != self.race.state:
            server = get_server_from_interaction(interaction)

            match race_state:
                case RaceState.Inactive:
                    # We only want to allow races to go to inactive state if there are NOT already
                    # submissions
                    if self.race_has_submissions:
                        await send_message(interaction, "ERROR: This race has submissions, can't change to Inactive state")
                        return
                case RaceState.Active:
                    # If we just activated the race there's a submit role for this category, clear the submit role
                    # from all users
                    if self.race.category_id.submit_role is not None:
                        submit_role = server.get_role(self.race.category_id.submit_role)
                        if submit_role is not None:
                            for m in interaction.guild.members:
                                await m.remove_roles(submit_role)

                    #  If there's a create role for this category, ask if we should send an announcement
                    if self.race.category_id.create_role is not None:
                        self.create_role = server.get_role(self.race.category_id.create_role)
                        if self.create_role is not None:
                            # Ask about pinging the create role
                            self.create_role_message = f"A new {self.race.category_id.name} race is now active!"
                            await send_message(interaction, f"The {self.create_role.name} role will be pinged with the message: {self.create_role_message} \
                                \n\nWould you like to edit the message? ('Cancel' will cancel the message from being sent)",
                                view=zYesNoCancelButtonView(yes_func = self.edit_create_role_message,
                                                            no_func = self.post_create_role_message,
                                                            cancel_func = self.on_create_role_message_cancel))
                case RaceState.Completed:
                    # If there are assigned racers and not all racers have submitted a time, we want to confirm before completing
                    assigned_racers = get_assigned_racers(self.race.id)
                    self.incomplete_assigned_race = False
                    self.should_score = True
                    if len(assigned_racers) > 0:
                        missing_submission = False
                        for a in assigned_racers:
                            s = get_race_submission(a.user_id, a.race_id)
                            if s is None:
                                missing_submission = True
                                break
                        if missing_submission:
                            self.incomplete_assigned_race = True
                            await send_message(interaction, f"Not all assigned racers have submitted a time, are you sure you want to mark the race as completed?",
                                view=zContinueCancelButtonView(continue_func = self.continue_complete_race,
                                                               no_func = self.cancel_race_state_change))
                    else:
                        self.complete_race(interaction)
                case _:
                    logging.info("  Unknown Race State choice")
                    await send_message(interaction, "ERROR: Unknown race state chosen. Contact bot admin")

            # Save the selected state
            self.race.state = race_state
            self.race.save()
            await send_message(interaction, "Race State Saved")

        else:
            await send_message("Race state NOT changed (same state selected as current state")

    #################################################################################################################
    async def cancel_race_state_change(self, interaction):
        await send_message(interaction, f"Race state change canceled")

    #################################################################################################################
    async def continue_complete_race(self, interaction):
        # If the race category has scoring, we want to ask if the incomplete race should be scored upon completion
        if self.race.category_id.points_type != PointsType.NoScoring:
            await send_message(interaction, f"",
                               view=zYesNoCancelButtonView(yes_func = self.complete_race,
                                                           no_func = self.complete_no_score,
                                                           cancel_func = self.cancel_race_state_change))
        else:
            await self.complete_race(interaction)

    #################################################################################################################
    async def complete_no_score(self, interaction):
        self.should_score = False
        await self.complete_race(interaction)

    #################################################################################################################
    async def complete_race(self, interaction):
        self.race.state = RaceState.Completed
        self.race.save()

        if self.should_score:
            score_race(self.race)

        await send_message(interaction, "Race Completed")

    #################################################################################################################
    async def on_create_role_message_cancel(self, interaction):
        await send_message(interaction, "Ping cancelled.")

    #################################################################################################################
    async def edit_create_role_message(self, interaction):
        ping_message_input = nextcord.ui.TextInput(
            label="Ping Message",
            required=True,
            default_value=self.create_role_message,
            row=1)
        await interaction.response.send_modal(zModal({"ping_message": ping_message_input},
            self.on_create_role_message_submit,
            "Edit Ping Message"))

    #################################################################################################################
    async def on_create_role_message_submit(self, interaction, modal):
        self.create_role_message = modal.children[0].value
        await self.post_create_role_message(interaction)

    #################################################################################################################
    async def post_create_role_message(self, interaction):
        server = get_server_from_interaction(interaction)
        channel = server.get_channel(self.race.server_id.announcement_channel_id)
        await channel.send(f"{self.create_role.mention} {self.create_role_message}")
        await send_message(interaction, "Message posted")

    #################################################################################################################
    async def on_race_extra_info_select(self, info_id_list, interaction):
        # Loop through the list of assignments for this race
        for i in self.race.extra_info_assignments:
            # remove rows that aren't in the user selected list
            if i.info_type_id not in info_id_list:
                i.delete_instance()
            else:
            # remove items from user list if they're already in the DB
                info_id_list.remove(i.info_type_id)

        # Loop through the remaining user selected list and create DB rows for them
        for i in info_id_list:
            a = AsyncRaceExtraInfoAssignment()
            a.info_type_id = i
            a.race_id = self.race.id
            a.save()

        await send_message(interaction, f"Saved extra info for race {self.race.id}")

    #################################################################################################################
    async def on_race_info_channel_select(self, channel_id, interaction):
        # Check if there's already a pinned race info message in this channel
        msgs = AsyncRaceMessage.select().where(AsyncRaceMessage.channel_id == channel_id)

        self.pin_channel_id = channel_id
        self.already_pinned_race = None
        # iterate through the list backwards to get the most recent first
        for m in msgs:
            for m in reversed(msgs):
                try:
                    self.already_pinned_race = AsyncRace.select().where(AsyncRace.race_info_message == m.id).get()
                    break
                except:
                    pass

        # If so, ask if they want to replace that message with this one
        if self.already_pinned_race is not None:
            await send_message(
                interaction,
                "There's a race already pinned in that channel. Do you want to REPLACE it with this one?",
                view=zYesNoButtonView(
                    yes_func = self.unpin_first,
                    no_func = self.pin_race))
        else:
            await self.pin_race(interaction)

    #################################################################################################################
    async def unpin_first(self, interaction):
        await unpin_race(self.already_pinned_race.id, interaction)
        await self.pin_race(interaction)

    #################################################################################################################
    async def pin_race(self, interaction):
        await pin_race_info(self.pin_channel_id, self.race, interaction)
        await send_message(interaction, "Done!")

    #################################################################################################################
    async def on_leaderboard_channel_select(self, channel_id, interaction):
        # Create new AsyncRaceMessage for the chosen channel
        new_db_msg = AsyncRaceMessage(server_id = interaction.guild_id, channel_id = channel_id)
        new_db_msg.save()

        # Save any existing leaderboard message id already stored
        old_db_msg_id = self.race.leaderboard_message

        # Save the new message id in the race
        self.race.leaderboard_message = new_db_msg.id
        self.race.save()

        # Delete the old AsyncRaceMessage and any discord message associated with it
        server = interaction.client.get_guild(interaction.guild_id)
        await delete_message(server, old_db_msg_id)

        await send_message(interaction, f"Leaderboard channel set for race {self.race.id}")

    #################################################################################################################
    async def on_race_role_select(self, role_id, interaction):
        self.race.submission_role = role_id
        self.race.save()
        await send_message(interaction, "Race Role Saved")

    #################################################################################################################
    async def select_racer(self, interaction):
        await send_message(interaction, view=zUserSelectView(self.assign_racer, placeholder="Choose wisely..."))

    #################################################################################################################
    async def assign_racer(self, user, interaction):
        # Create a race assignment for this user
        logging.info(f"  Assigning {user.id} - {user.name} to race {self.race.id}")
        assign_racer(user.id, self.race.id)
        # Ask if there are more users to assign. If not we're done, if so loop back to sending the UserSelect
        await send_message(interaction,
                           "Are there more racers to assign?",
                           view=zYesNoButtonView(self.select_racer,
                                                 lambda interaction : send_message(interaction, "Done!")))

########################################################################################################################
# Racer Actions
#####################################################################################################################
# Handles a user race submission action
class zRaceSubmitHandler():
    def __init__(self, race_id, submission=None):
        self.race = get_race(race_id)
        self.submission = submission

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
                   label="Enter IGT in format `H:MM:SS`",
                   default_value=submission.finish_time if submission is not None else None,
                   required=True),
            zField(custom_id=self.comment_id,
                   label="Comment",
                   default_value=submission.comment if submission is not None else None,
                   required=False),
        ]

        # Add any extra info fields
        for a in self.race.extra_info_assignments:
            t = get_extra_info_type(a.info_type_id)
            info = get_extra_info(self.submission, a.info_type_id)
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
            self.submission.user_id = interaction.user.id
            self.submission.submit_datetime = zBot_now()

        msg = f"Submission Info:\n"
        for i, v in enumerate(submitted_values):
            msg += f"\n  {self.fields[i].custom_id}: {v}"
            match self.fields[i].custom_id:
                case self.finish_time_id:
                    self.submission.finish_time = v
                    self.submission.save()
                case self.comment_id:
                    self.submission.comment = v
                case _:
                    self.save_extra_info(self.fields[i], v)
        msg += f"  Race ID: {self.race.id}"

        self.submission.save()
        await send_message(interaction, "Race Submission Saved")

    ####################################################################################################################
    # Saves an individual extra info value
    def save_extra_info(self, field: zField, value):
        # We store the info_type_id in the custom ID of the zField
        info = get_extra_info(self.submission, field.custom_id)
        # We need to create a new DB entry
        if info is None:
            info = AsyncRaceExtraInfo()
            info.submission_id = self.submission.id
            info.info_type_id = int(field.custom_id)
        # == TODO ==
        # Validate the value passed in based on the info type
        # == TODO ==
        info.data = value
        info.save()

########################################################################################################################
# Racer button view: Contains buttons used to show racer stats, display a list of assigned and open races and
# get race info
class zRacerButtonView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='📊 My Stats')
    async def stats_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await send_message(interaction, "Stats coming soon!")

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='🏁 Open Races')
    async def open_races_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Ask the user which categories they'd like to view
        cat_select_list = get_category_select_list(interaction.guild.id)
        await send_message(interaction, view=zMultiSelectView(cat_select_list,
                                                              len(cat_select_list),
                                                              self.on_category_select,
                                                              "Select categories to view..."))

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='👉🏾 Assigned Races')
    async def assigned_races_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        races = get_assigned_races(interaction.user.id, interaction.guild.id)
        table_text = get_race_list_table(races, interaction.guild.id)
        await send_message(interaction, table_text, codeblock=True)

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='📋 Get Race Details')
    async def race_details_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Get list of races that the user has access to
        open_races = [r for r in get_open_races(interaction.guild.id)]
        assigned_races = [r for r in get_assigned_races(interaction.user.id, interaction.guild.id)]
        races = open_races + assigned_races
        race_select_list = []
        for r in races:
            race_select_list.append(nextcord.SelectOption(label=r.description, value=r.id, description=r.description))
        await send_message(interaction, view=zSingleSelectView(race_select_list,
                                                               self.on_race_select,
                                                               "Select race to view..."))

    #################################################################################################################
    async def on_category_select(self, categories, interaction):
        # Get list of races with those categories
        open_races = get_open_races(interaction.guild.id)

        # Filter the list based on the chosen categories
        races = []
        for r in open_races:
            if r.category_id.id in categories:
                races.append(r)

        if len(races) == 0:
            await send_message(interaction, "There are no open races in those categories")
            return

        table_text = get_race_list_table(races, interaction.guild.id)
        await send_message(interaction, table_text, codeblock=True)

    #################################################################################################################
    async def on_race_select(self, race_id, interaction):
        race = get_race(race_id)
        if race is None:
            await send_message(interaction, "Error occurred, could not find race data. Please contact a bot admin")
            return
        msg_text, seed_embed = get_race_info_message(race)
        await send_message(interaction, msg_text, view=zRaceInfoButtonView(race.id), embed=seed_embed)

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
        await display_ephemeral_leaderboard(interaction, self.race_id)

#################################################################################################################
async def pin_race_info(channel_id, race, interaction):
    # Get the channel
    server = get_server_from_interaction(interaction)
    channel = server.get_channel(channel_id)

    if channel is not None:
        msg = await post_race_info_message(race, channel)

        # Create a new AsyncRaceMessage with the race info message info
        new_db_msg = AsyncRaceMessage()
        new_db_msg.server_id = interaction.guild_id
        new_db_msg.channel_id = channel_id
        new_db_msg.message_id = msg.id
        new_db_msg.save()

        # Update the race with the new race info message id
        old_db_msg_id = race.race_info_message
        race.race_info_message = new_db_msg.id
        race.save()

        # Finally delete the old message if it exists
        await delete_message(server, old_db_msg_id)
    else:
        logging.info(f"Could not find channel with id {channel_id}")

####################################################################################################################
async def post_race_info_message(race, channel):
    msg_text, seed_embed = get_race_info_message(race)
    return await channel.send(msg_text, view=zRaceInfoButtonView(race.id), embed=seed_embed)

