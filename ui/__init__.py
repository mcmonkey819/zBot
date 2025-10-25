# -*- coding: utf-8 -*-
"""
UI package for zBot Discord bot.
Contains UI utilities, menus, and string data for user interactions.
"""

# Import all UI modules to make them available at package level
from . import menus_string_data
from . import ui_util

# Conditionally import menus to handle nextcord.ext.menus import issues
try:
    from . import menus
    _menus_available = True
except ImportError:
    _menus_available = False
    menus = None

# Make commonly used classes and functions available for direct import
from .ui_util import (
    zField, zModal, zSingleSelect, zSingleSelectView, zMultiSelect, zMultiSelectView,
    zUserSelect, zUserSelectView, zContinueCancelButtonView, zYesNoButtonView,
    zMultiPageModalSender, send_message, defer, user_is_admin, user_is_mod,
    save_message, delete_message, get_race_info_message, build_response_message_list
)

# Only import from menus if it's available
if _menus_available:
    from .menus import (
        zButton, zButtonMenu, zConfirmMenu, zConfirmThreeOptionMenu, zToggleButton,
        zToggleButtonMenu, zRaceListPageSource, zRaceListMenuPages, MenuItem,
        EmbedField, ToggleField, prompt_for_channel, pin_race_info, pin_race_for_category
    )

# Version info
__version__ = "1.0.0"
__author__ = "zBot Development Team"
