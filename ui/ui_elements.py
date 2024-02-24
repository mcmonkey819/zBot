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
                AsyncRaceExtraInfoAssignment.server_id == self.server_id)
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
        self.stop()

########################################################################################################################
# Racer Actions
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
        if include_points and self.race.category_id.points_type != PointsType.NoScoring:
            self.fields.append(zField(custom_id=self.points_id,
                                      label="Points",
                                      default_value=submission.points if submission is not None else None,
                                      placeholder="Category points for this submission",
                                      required=False))

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
            self.submission.user_id = self.user_id if self.user_id is not None else interaction.user.id
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
                case self.points_id:
                    try:
                        self.submission.points = int(v)
                    except:
                        await send_message(interaction, "**ERROR** Points must be an integer")
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

    if channel is None:
        logging.info(f"Could not find channel with id {channel_id}")
        return False
    
    msg = await post_race_info_message(race, channel)
    await msg.pin()
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
async def post_race_info_message(race, channel):
    msg_text, seed_embed = get_race_info_message(race)
    msg = await channel.send(msg_text, view=zRaceInfoButtonView(race.id), embed=seed_embed)
    await msg.pin()
    return msg

