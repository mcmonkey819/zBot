# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, date
import logging
from nextcord.ext import commands
import nextcord
import re
import validators

from db.zBot_db_orm import *

########################################################################################################################
# UTILITY TYPES
########################################################################################################################
FieldList = dict[str, nextcord.ui.TextInput]
SelectList = list[nextcord.SelectOption]

VarTypeInt      = 1
VarTypeStr      = 2
VarTypeGameTime = 3
VarTypeDateTime = 4

VartypeStrDict = {
    VarTypeInt:       "Integer",
    VarTypeStr:       "String",
    VarTypeGameTime:  "Game Time (H:MM:SS)",
    VarTypeDateTime:  "Date/Time",
}

VartypeSelectOptionList = [
    nextcord.SelectOption(label="Integer", value=VarTypeInt, description="Integer Value"),
    nextcord.SelectOption(label="String", value=VarTypeStr, description="String text up to 255 characters in length"),
    nextcord.SelectOption(label="Game Time (H:MM:SS)", value=VarTypeGameTime, description="Game time expressed in 'H:MM:SS' format"),
    nextcord.SelectOption(label="Date/Time", value=VarTypeDateTime, description="Date & Time string, typically something like 'YYYY-MM-DD HH:MM:SS'"),
]

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

#####################################################################################################################
def get_extra_info_type_select_list(server_id, race =None):
    # Get the list of extra info types for this server
    types = AsyncRaceExtraInfoType.select().where(AsyncRaceExtraInfoType.server_id == server_id)
    default_list = []
    if race is not None:
        for r in race.extra_info_assignments:
            default_list.append(r.info_type_id.id)

    # Populate the SelectOption list with the race information
    select_list = []
    for t in types:
        select_list.append(nextcord.SelectOption(label=f"{t.name}", value=t.id, description=t.description, default=t.id in default_list))
    return select_list

#####################################################################################################################
def get_race_extra_info(race_id):
    infos = []
    if race_id is not None:
        infos = AsyncRaceExtraInfoAssignment.select().where(AsyncRaceExtraInfoAssignment.race_id == race_id)
    return infos

####################################################################################################################
# Takes an AsyncRaceMessage, finds the corresponding Discord message and deletes both the message and DB entry
async def delete_message(server, async_race_msg_id):
    async_race_msg = None
    if async_race_msg_id is not None:
        try:
            async_race_msg = AsyncRaceMessage.select().where(AsyncRaceMessage.id == async_race_msg_id).get()
        except:
            logging.info(f"Failed to find AsyncRaceMessage with ID {async_race_msg_id}")

    if async_race_msg is not None:
        if async_race_msg.message_id is not None:
            channel = server.get_channel(async_race_msg.channel_id)
            try:
                msg = await channel.fetch_message(async_race_msg.message_id)
                await msg.delete()
            except:
                logging.info(f"Failed to find message with message ID {async_race_msg.message_id}")
        async_race_msg.delete_instance()

#####################################################################################################################
async def has_text_channel_permission(user_id, server, channel):
    ret = False

    member = await server.fetch_member(user_id)
    perms = channel.permissions_for(member)
    bot_text_permission = nextcord.Permissions.text()
    bot_text_permission.update(manage_messages=False, manage_threads=False, send_tts_messages=False)
    if perms.is_superset(bot_text_permission):
        ret = True

    return ret

#####################################################################################################################
async def get_permitted_channel_select_list(user_id, server):
    select_list = []
    for c in server.text_channels:
        if await has_text_channel_permission(user_id, server, c):
            select_list.append(nextcord.SelectOption(label=c.name, value=c.id, description=c.name))
    return select_list

#####################################################################################################################
def get_role_select_list(server):
    select_list = []
    for r in server.roles:
        select_list.append(nextcord.SelectOption(label=r.name, value=r.id, description=r.name))
    return select_list

#####################################################################################################################
def get_race(race_id):
    race = None
    if race_id is not None:
        try:
            race = AsyncRace.select().where(AsyncRace.id == race_id).get()
        except:
            logging.info(f"Could not find race ID {race_id}")
    return race

#####################################################################################################################
def get_category(category_id):
    category = None
    if category_id is not None:
        try:
            category = AsyncRaceCategory.select().where(AsyncRaceCategory.id == category_id).get()
        except:
            logging.info(f"Could not find category ID {category_id}")
    return category

#####################################################################################################################
def get_extra_info_type(info_type_id):
    info_type = None
    if info_type_id is not None:
        try:
            info_type = AsyncRaceExtraInfoType.select().where(AsyncRaceExtraInfoType.id == info_type_id).get()
        except:
            logging.info(f"Could not find Info Type ID {info_type_id}")
    return info_type

#####################################################################################################################
# Returns the current date/time in the format used in the database
def zBot_now():
    return datetime.now().isoformat(timespec='minutes').replace('T', ' ')

#####################################################################################################################
def check_server_assignment_exists(info_type_id, server_id):
    try:
        a = AsyncRaceExtraInfoAssignment.select().where(
            AsyncRaceExtraInfoAssignment.info_type_id == info_type_id and
            AsyncRaceExtraInfoAssignment.server_id == server_id).get()
    except:
        a = None
    return a is not None

#####################################################################################################################
def check_category_assignment_exists(info_type_id, category_id):
    try:
        a = AsyncRaceExtraInfoAssignment.select().where(
                AsyncRaceExtraInfoAssignment.info_type_id == info_type_id and
                AsyncRaceExtraInfoAssignment.category_id == category_id).get()
    except:
        a = None
    return a is not None