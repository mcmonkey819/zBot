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

# This Select (drop down selection) will display a drop down with the string options provided.
# This variant will only allow the user to select a single option from the list
# On completion it will call the provided submit_handler function, passing caller_data
# along with the value for the option chosen and the interaction object.
class zSingleSelect(nextcord.ui.Select):
    def __init__(self, select_list: SelectList, submit_handler, caller_data = None):
        super().__init__(min_values=1, max_values=1, options=select_list)
        self.submit_handler = submit_handler
        self.caller_data = caller_data

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.submit_handler(self.caller_data, interaction.data['values'][0], interaction)

# View which contains a zSingleSelect
class zSingleSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, submit_handler, caller_data = None):
        super().__init__(timeout=None)
        self.category_select = zSingleSelect(select_list, submit_handler, caller_data)
        self.add_item(self.category_select)

# This Select (drop down selection) will display a drop down with the string options provided.
# This variant will allow the user to select up to `max_values` from the list
# On completion it will call the provided submit_handler function, passing caller_data
# along with a list of the values chosen and the interaction object.
class zMultiSelect(nextcord.ui.Select):
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, caller_data = None):
        super().__init__(min_values=1, max_values=max_values, options=select_list)
        self.submit_handler = submit_handler
        self.caller_data = caller_data

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.submit_handler(self.caller_data, interaction.data['values'], interaction)

# View which contains a zMultiSelect
class zMultiSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, caller_data = None):
        super().__init__(timeout=None)
        self.category_select = zMultiSelect(select_list, max_values, submit_handler, caller_data)
        self.add_item(self.category_select)

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



# View which contains category moderation buttons
class zCategoryModView(nextcord.ui.View):
    def __init__(self, add_func, edit_func):
        super().__init__(timeout=None)
        self.add_func = add_func
        self.edit_func = edit_func

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➕ Add Category')
    async def add_category_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Create and send Add Category modal, passing the caller provided add_func to be called when submitted
        await interaction.response.send_modal(zCategoryAddEditModal(None))

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='✏️ Edit Category')
    async def edit_category_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Get the list of categories for this server
        categories = AsyncRaceCategory.select().where(AsyncRaceCategory.server_id == interaction.guild_id)

        if len(categories) == 0:
            await interaction.send("No categories defined for this server", ephemeral=True)
            return

        # Create and send category Select view, calling the category select handler
        select_list = []
        for c in categories:
            select_list.append(nextcord.SelectOption(label=c.name, value=c.id, description=c.description))
        self.cat_select = zSingleSelectView(select_list, self.on_category_select, self)
        await interaction.send(view=self.cat_select, ephemeral=True)

    async def on_category_select(self, caller_data, category_id, interaction):
        # Create and send Edit Category modal, passing the caller provided edit_func to be called when submitted
        await interaction.response.send_modal(zCategoryAddEditModal(category_id))