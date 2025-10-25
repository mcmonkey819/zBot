# -*- coding: utf-8 -*-
"""
Mock menus module for testing.
Provides the necessary menu classes that are used in the codebase.
"""
from unittest.mock import Mock

# Create mock menu classes that properly handle inheritance
class ButtonMenu:
    def __init__(self, *args, **kwargs):
        pass
    
    def __init_subclass__(cls, **kwargs):
        # Allow keyword arguments in __init_subclass__
        pass

class Menu:
    @staticmethod
    async def start(self, interaction=None, wait=False):
        pass

class ListPageSource:
    def __init__(self, *args, **kwargs):
        pass

class ButtonMenuPages:
    def __init__(self, *args, **kwargs):
        pass
    
    def __init_subclass__(cls, **kwargs):
        # Allow keyword arguments in __init_subclass__
        pass

# Create a mock module
menus = Mock()
menus.ButtonMenu = ButtonMenu
menus.Menu = Menu
menus.ListPageSource = ListPageSource
menus.ButtonMenuPages = ButtonMenuPages
