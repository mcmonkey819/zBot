# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, date
import logging
from nextcord.ext import commands
import nextcord
import re
from typing import Any, Callable
from db.zBot_db_orm import *

FieldList = dict[str, nextcord.ui.Item]
SelectList = list[nextcord.SelectOption]

########################################################################################################################
# UTILITY FUNCTIONS
########################################################################################################################
def get_category_select_list(server_id):
    # Get the list of categories for this server
    categories = AsyncRaceCategory.select().where(AsyncRaceCategory.server_id == server_id)

    # Populate the SelectOption list with the category information
    select_list = []
    for c in categories:
        select_list.append(nextcord.SelectOption(label=c.name, value=c.id, description=c.description))
    return select_list

#####################################################################################################################
def get_race_select_list(server_id):
    # Get the list of race for this server
    races = AsyncRace.select().where(AsyncRace.server_id == server_id)

    # Populate the SelectOption list with the race information
    select_list = []
    for r in races:
        select_list.append(nextcord.SelectOption(label=f"{r.id} - {r.description[:15]}", value=r.id, description=r.description))
    return select_list

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
        await self.submit_handler(self.caller_data, interaction.data['values'][0], interaction)

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
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, placeholder = None, caller_data = None):
        super().__init__(min_values=1, max_values=max_values, options=select_list, placeholder=placeholder)
        self.submit_handler = submit_handler
        self.caller_data = caller_data

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.submit_handler(self.caller_data, interaction.data['values'], interaction)

#####################################################################################################################
# View which contains a zMultiSelect
class zMultiSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, caller_data = None):
        super().__init__(timeout=None)
        self.category_select = zMultiSelect(select_list, max_values, submit_handler, caller_data)
        self.add_item(self.category_select)

########################################################################################################################
# MODALS
########################################################################################################################
# Modal which has fields required to create/edit a category
class zCategoryAddEditModal(zModal):
    def __init__(self, category_id=None):
        # Lookup the category if an ID was provided
        category = None
        if category_id is not None:
            try:
                category = AsyncRaceCategory.select().where(AsyncRaceCategory.id == category_id).get()
            except:
                logging.info(f"Could not find category ID {category_id}")
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
            self.race.state = "INACTIVE"
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

########################################################################################################################
# BUTTON VIEWS
########################################################################################################################
# View which contains category moderation buttons
class zCategoryModView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➕ Add Category')
    async def add_category_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Create and send Add Category modal
        await interaction.response.send_modal(zCategoryAddEditModal(None))

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='✏️ Edit Category')
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
        await interaction.response.send_modal(zCategoryAddEditModal(int(category_id)))

#####################################################################################################################
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
        edit_select_list = [ 
            nextcord.SelectOption(label="Edit Race Info",          value=0, description="Edit the seed, hash or description"),
            nextcord.SelectOption(label="Change Race State",       value=1, description="Set the race as Active, Inactive or Closed"),
            nextcord.SelectOption(label="Pin Race Info",           value=2, description="Create a message with race info and buttons for submit actions"),
            nextcord.SelectOption(label="Set Leaderboard Channel", value=3, description="Set a channel to display the race leaderboard in"),
            nextcord.SelectOption(label="Set Submit Role",         value=4, description="Choose a role to be assigned when a racer submits a time for this race"),
            ]
        try:
            self.race = AsyncRace.select().where(AsyncRace.id == int(race_id)).get()
        except:
            self.race = None

        if self.race is None:
            err_msg = "ERROR: Race not found in DB"
            logging.info(err_msg)
            await interaction.send(err_msg, ephemeral=True)
            return

        edit_select_view = zSingleSelectView(edit_select_list, self.on_edit_select, "Choose Edit Action...", self)
        await interaction.send(view=edit_select_view, ephemeral=True)

    #################################################################################################################
    async def on_edit_select(self, caller_data, edit_choice, interaction):
        match int(edit_choice):
            case 0:
                logging.info("  Edit Race Selected")
                await self.send_race_modal(self.race, self.race.category_id, interaction)
            case 1:
                logging.info("  Change Race State Selected")
            case 2:
                logging.info("  Pin Race Info Selected")
            case 3:
                logging.info("  Set Leaderboard Channel Selected")
            case 4:
                logging.info("  Set Race Role Selected")
            case _:
                logging.info("  Unknown Edit Choice")
