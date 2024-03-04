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

        await send_message(interaction, "Race Info Saved")
        self.stop()

