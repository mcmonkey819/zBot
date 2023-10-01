# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, date
import logging
from nextcord.ext import commands
import nextcord
import re

from db.zBot_db_orm import *
from ui.ui_util import *

########################################################################################################################
# BASE CLASSES
########################################################################################################################
# This Modal (form) will display a form that has fields matching the provided item list.
# On completion it will call the provided submit_handler function, passing caller_data
# along with a pointer to itself and the interaction object.
class zModal(nextcord.ui.Modal):
    def __init__(self, fields: FieldList, submit_handler, title: str, caller_data = None):
        super().__init__(title, timeout=None)
        self.fields = fields
        self.submit_handler = submit_handler
        self.caller_data = caller_data

        for v in self.fields.values():
            self.add_item(v)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.submit_handler(self.caller_data, interaction, self)

#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided.
# This variant will only allow the user to select a single option from the list
# On completion it will call the provided submit_handler function, passing caller_data
# along with the value for the option chosen and the interaction object.
class zSingleSelect(nextcord.ui.Select):
    def __init__(self, select_list: SelectList, submit_handler, placeholder, caller_data = None):
        super().__init__(min_values=1, max_values=1, options=select_list, placeholder=placeholder)
        self.submit_handler = submit_handler
        self.caller_data = caller_data

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.submit_handler(self.caller_data, int(interaction.data['values'][0]), interaction)

#####################################################################################################################
# View which contains a zSingleSelect
class zSingleSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, submit_handler, placeholder = None, caller_data = None):
        super().__init__(timeout=None)
        self.category_select = zSingleSelect(select_list, submit_handler, placeholder, caller_data)
        self.add_item(self.category_select)

#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided.
# This variant will allow the user to select up to `max_values` from the list
# On completion it will call the provided submit_handler function, passing caller_data
# along with a list of the values chosen and the interaction object.
class zMultiSelect(nextcord.ui.Select):
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, placeholder, caller_data = None):
        super().__init__(min_values=1, max_values=max_values, options=select_list, placeholder=placeholder)
        self.submit_handler = submit_handler
        self.caller_data = caller_data

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value_list = []
        for v in interaction.data['values']:
            value_list.append(int(v))
        await self.submit_handler(self.caller_data, value_list, interaction)

#####################################################################################################################
# View which contains a zMultiSelect
class zMultiSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, placeholder = None, caller_data = None):
        super().__init__(timeout=None)
        self.category_select = zMultiSelect(select_list, max_values, submit_handler, placeholder, caller_data)
        self.add_item(self.category_select)

########################################################################################################################
# MODALS
########################################################################################################################
# Modal which has fields required to create/edit a category
class zCategoryAddEditModal(zModal):
    def __init__(self, category_id=None):
        # Lookup the category if an ID was provided
        category = get_category(category_id)

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
        super().__init__(fields, self.on_submit, title, None)


    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, caller_data, interaction, modal):
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
            await interaction.send(f"Saved category {self.category.name}", ephemeral=True)
        except:
            await interaction.send(f"FAILED to save category {self.category.name}", ephemeral=True)

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
        super().__init__(fields, self.on_submit, title, None)


    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, caller_data, interaction, modal):
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
        vartype_select_view = zSingleSelectView(VartypeSelectOptionList, self.on_vartype_select, "Choose Data Type...", self)
        await interaction.send(view=vartype_select_view, ephemeral=True)

    async def on_vartype_select(self, caller_data, vartype, interaction):
        self.info_type.var_type = vartype
        try:
            self.info_type.save()
            await interaction.send(f"Saved info type {self.info_type.name}", ephemeral=True)
        except:
            await interaction.send(f"FAILED to save info type {self.info_type.name}", ephemeral=True)

#####################################################################################################################
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
        super().__init__(fields, self.on_submit, title, None)

    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, caller_data, interaction, modal):
        # If we don't already have a DB entry create one now
        if self.race is None:
            self.race = AsyncRace()
            self.race.server_id = self.server_id
            self.race.category_id = self.category_id
            self.race.create_datetime = date.today().isoformat()
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
        self.race.save()
        logging.info(msg)

        await interaction.send("Race Info Saved", ephemeral=True)

#####################################################################################################################
# Modal which has fields required to submit a race time
class zRaceSubmissionModal(zModal):
    def __init__(self, race_id, submission=None):
        self.race_id = race_id
        self.submission = submission

        # Set the title
        if submission is None:
            title = "Submit TIme"
        else:
            title = f"Edit Submission"

        self.finish_time_id = "finish_time"
        self.comment_id     = "comment"
        self.vod_link_id    = "vod_link"

        # Create the modal fields
        fields = {
            self.finish_time_id: nextcord.ui.TextInput(
                label="Finish Time (H:MM:SS)",
                required=True,
                custom_id=self.finish_time_id,
                row=1,
                default_value=submission.finish_time if submission is not None else None),
            self.comment_id: nextcord.ui.TextInput(
                label="Comment",
                required=False,
                custom_id=self.comment_id,
                row=2,
                default_value=submission.comment if submission is not None else None),
            self.vod_link_id: nextcord.ui.TextInput(
                label="VoD Link",
                required=False,
                custom_id=self.vod_link_id,
                row=3,
                default_value=submission.vod_link if submission is not None else None),
        }
        # Call the base class init
        super().__init__(fields, self.on_submit, title, None)

    # Takes the data submitted by the user and saves it to the DB
    async def on_submit(self, caller_data, interaction, modal):
        # If we don't already have a DB entry create one now
        if self.submission is None:
            self.submission = AsyncRaceSubmission()
            self.submission.race_id = self.race_id
            self.submission.user_id = interaction.user.id
            self.submission.submit_datetime = zBot_now()

        msg = f"Saved Submission Info:\n"
        for c in modal.children:
            match c.custom_id:
                case self.finish_time_id:
                    #if game_time_is_valid(c.value) == False:
                    #    await interaction.send("Invalid Time, please use 'H:MM:SS' format", ephemeral=True)
                    #    return
                    self.submission.finish_time = c.value
                    msg += "  Finish Time: "
                case self.comment_id:
                    if c.value is not None:
                        self.submission.comment = c.value
                    msg += "  Comment: "
                case self.vod_link_id:
                    self.submission.vod_link = c.value
                    msg += "  VoD Link: "
                case _:
                    continue
            msg += f"{c.value}\n"
        msg += f"  Race ID: {self.race_id}"

        self.submission.save()
        logging.info(msg)
        await interaction.send("Race Submission Saved", ephemeral=True)

########################################################################################################################
# BUTTON VIEWS
########################################################################################################################
# View which contains race info buttons
class zRaceInfoButtonView(nextcord.ui.View):
    def __init__(self, race_id):
        super().__init__(timeout=None)
        self.race_id = race_id

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='⏱️ Submit/Edit Time')
    async def submit_time_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Lookup if the user has a submission for this race already
        submission = None
        await interaction.response.send_modal(zRaceSubmissionModal(self.race_id, submission))

    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='🏳️ Forfeit Race')
    async def forfeit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        ## TODO ##
        await interaction.send("Forfeit Coming Soon")

    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='🥇 Leaderboard')
    async def leaderboard_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        ## TODO ##
        await interaction.send("Leaderboard Coming Soon")

########################################################################################################################
# View which contains category moderation buttons
class zCategoryModView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='➕ Add Category')
    async def add_category_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Create and send Add Category modal
        await interaction.response.send_modal(zCategoryAddEditModal(None))

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='✏️ Edit Category')
    async def edit_category_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Get the list of categories for this server
        select_list = get_category_select_list(interaction.guild_id)

        if len(select_list) == 0:
            await interaction.send("No categories defined for this server", ephemeral=True)
            return

        # Create and send category Select view, calling the category select handler
        self.cat_select = zSingleSelectView(select_list, self.on_category_select, "Select a Category", self)
        await interaction.send(view=self.cat_select, ephemeral=True)

    async def on_category_select(self, caller_data, category_id, interaction):
        # Create and send Edit Category modal
        await interaction.response.send_modal(zCategoryAddEditModal(category_id))

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='➕ Add Submit Info Type')
    async def add_submit_info_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Create and send Add Category modal
        await interaction.response.send_modal(zExtraInfoTypeAddEditModal(None))

    ####################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.green, label='👉🏾 Assign Extra Info')
    async def assign_extra_info_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Prompt to select from list of extra info types
        select_view = zSingleSelectView(get_extra_info_type_select_list(interaction.guild.id), self.on_info_type_select, "Select info type to assign...", self)
        await interaction.send(view=select_view, ephemeral=True)

    async def on_info_type_select(self, caller_data, info_type_choice, interaction):
        self.info_type_choice = info_type_choice
        # Prompt for what to assign to: server or category
        self.server_choice_id = 1
        self.cat_choice_id = 2
        select_list = [
            nextcord.SelectOption(label="Server", value=self.server_choice_id, description="Assign extra info to be set by default for this server"),
            nextcord.SelectOption(label="Category", value=self.cat_choice_id, description="Assign extra info to be set by default for a race category"),
            ]
        select_view = zSingleSelectView(select_list, self.on_assign_type_select, "Select what to assign to...", self)
        await interaction.send(view=select_view, ephemeral=True)

    async def on_assign_type_select(self, caller_data, assign_choice, interaction):
        if assign_choice == self.server_choice_id:
            # Check to see if this assignment has already been made
            if check_server_assignment_exists(self.info_type_choice, interaction.guild.id):
                await interaction.send("Assignment already exists", ephemeral=True)
                return
            # Then create a new DB assignment with the selected info
            assignment = AsyncRaceExtraInfoAssignment()
            assignment.info_type_id = self.info_type_choice
            assignment.server_id = interaction.guild.id
            assignment.save()
            await interaction.send("Assignment saved", ephemeral=True)
        else:
            # Send a select to prompt for which category to assign to
            cat_select_view = zSingleSelectView(get_category_select_list(interaction.guild.id), self.on_cat_assign_select, "Select Category...", self)
            await interaction.send(view=cat_select_view, ephemeral=True)

    async def on_cat_assign_select(self, caller_data, category_id, interaction):
        category_id = category_id
        # Check to see if this assignment has already been made
        if check_category_assignment_exists(self.info_type_choice, category_id):
                await interaction.send("Assignment already exists", ephemeral=True)
                return
        # Then create a new DB assignment with the selected info
        assignment = AsyncRaceExtraInfoAssignment()
        assignment.info_type_id = self.info_type_choice
        assignment.category_id = category_id
        assignment.save()
        await interaction.send("Assignment saved", ephemeral=True)

########################################################################################################################
# Race Mod buttons: Edit Race Info, Edit Category/Role/Leaderboard Channel, Change Race State, Pin Race Info
# View which contains race moderation buttons
class zRaceModView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➕ Add Race')
    async def add_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Prompt the user to select a category for the race, then send the add race modal
        await interaction.send(view=zSingleSelectView(
            get_category_select_list(interaction.guild_id),
            self.send_race_modal,
            "Select Race Category",
            None), ephemeral=True)

    #################################################################################################################
    async def send_race_modal(self, race, category_id, interaction):
        await interaction.response.send_modal(zRaceAddEditModal(interaction.guild_id, category_id, race))

    #################################################################################################################
    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='️️️️✏️ Edit Race')
    async def edit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        race_select_view = zSingleSelectView(
            get_race_select_list(interaction.guild_id),
            self.on_race_select,
            "Choose Race to Edit...",
            self)
        await interaction.send(view=race_select_view, ephemeral=True)

    #################################################################################################################
    async def on_race_select(self, caller_data, race_id, interaction):
        try:
            self.race = AsyncRace.select().where(AsyncRace.id == race_id).get()
        except:
            self.race = None

        if self.race is None:
            err_msg = "ERROR: Race not found in DB"
            logging.info(err_msg)
            await interaction.send(err_msg, ephemeral=True)
            return

        state_label = "Deactivate Race" if self.race.active else "Mark Race Active"
        state_desc = "Set the race as inactive, preventing new submissions" if self.race.active else "Mark the race active, allowing new submissions"
        self.edit_info_id = 0
        self.edit_state_id = 1
        self.edit_extra_info_id = 2
        self.pin_race_info_id = 3
        self.set_leaderboard_channel_id = 4
        self.set_submit_role_id = 5
        edit_select_list = [ 
            nextcord.SelectOption(label="Edit Race Info",          value=self.edit_info_id, description="Edit the seed, hash or description"),
            nextcord.SelectOption(label=state_label,               value=self.edit_state_id, description=state_desc),
            nextcord.SelectOption(label="Edit Extra Info",         value=self.edit_extra_info_id, description="Edit what extra info will be stored on submissions"),
            nextcord.SelectOption(label="Pin Race Info",           value=self.pin_race_info_id, description="Create a message with race info and buttons for submit actions"),
            nextcord.SelectOption(label="Set Leaderboard Channel", value=self.set_leaderboard_channel_id, description="Set a channel to display the race leaderboard in"),
            nextcord.SelectOption(label="Set Submit Role",         value=self.set_submit_role_id, description="Choose a role to be assigned when a racer submits a time for this race"),
            ]
        edit_select_view = zSingleSelectView(edit_select_list, self.on_edit_select, "Choose Edit Action...", self)
        await interaction.send(view=edit_select_view, ephemeral=True)

    #################################################################################################################
    async def on_edit_select(self, caller_data, edit_choice, interaction):
        server = interaction.client.get_guild(interaction.guild_id)
        match edit_choice:
            case self.edit_info_id:
                logging.info("  Edit Race Selected")
                await self.send_race_modal(self.race, self.race.category_id, interaction)
            case self.edit_state_id:
                logging.info("  Change Race State Selected")
                # Toggle the active state
                self.race.active = self.race.active ^ True
                self.race.save()
                await interaction.send("Race State Saved", ephemeral=True)
            case self.edit_extra_info_id:
                logging.info("  Edit Race Extra Info Selected")
                info_list = get_extra_info_type_select_list(interaction.guild.id, self.race)
                if len(info_list) > 0:
                    await interaction.send(view=zMultiSelectView(info_list, len(info_list), self.on_race_extra_info_select, "Choose Info(s)...", self), ephemeral=True)
                else:
                    await interaction.send("No extra info types defined for this server")
            case self.pin_race_info_id:
                logging.info("  Pin Race Info Selected")
                channel_list = await get_permitted_channel_select_list(interaction.client.user.id, server)
                await interaction.send(view=zSingleSelectView(channel_list, self.on_race_info_channel_select, "Choose Channel...", self), ephemeral=True)
            case self.set_leaderboard_channel_id:
                logging.info("  Set Leaderboard Channel Selected")
                channel_list = await get_permitted_channel_select_list(interaction.client.user.id, server)
                await interaction.send(view=zSingleSelectView(channel_list, self.on_leaderboard_channel_select, "Choose Channel...", self), ephemeral=True)
            case self.set_submit_role_id:
                logging.info("  Set Race Role Selected")
                role_list = get_role_select_list(server)
                await interaction.send(view=zSingleSelectView(role_list, self.on_race_role_select, "Choose Role...", self), ephemeral=True)
            case _:
                logging.info("  Unknown Edit Choice")

    #################################################################################################################
    async def on_race_extra_info_select(self, caller_data, info_id_list, interaction):
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

        await interaction.send(f"Saved extra info for race {self.race.id}", ephemeral=True)

    #################################################################################################################
    async def on_race_info_channel_select(self, caller_data, channel_id, interaction):
        # Get the channel
        server = interaction.client.get_guild(interaction.guild_id)
        channel = server.get_channel(channel_id)

        if channel is not None:
            msg = await post_race_info_message(self.race, channel)

            # Create a new AsyncRaceMessage with the race info message info
            new_db_msg = AsyncRaceMessage()
            new_db_msg.server_id = interaction.guild_id
            new_db_msg.channel_id = channel_id
            new_db_msg.message_id = msg.id
            new_db_msg.save()

            # Update the race with the new race info message id
            old_db_msg_id = self.race.race_info_message
            self.race.race_info_message = new_db_msg.id
            self.race.save()

            # Finally delete the old message if it exists
            await delete_message(server, old_db_msg_id)
        else:
            logging.info(f"Could not find channel with id {channel_id}")

    #################################################################################################################
    async def on_leaderboard_channel_select(self, caller_data, channel_id, interaction):
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

        await interaction.send(f"Leaderboard channel set for race {self.race.id}", ephemeral=True)

    #################################################################################################################
    async def on_race_role_select(self, caller_data, role_id, interaction):
        self.race.submission_role = role_id
        self.race.save()
        await interaction.send("Race Role Saved", ephemeral=True)
