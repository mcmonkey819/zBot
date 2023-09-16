import sys
import nextcord
from nextcord.ext import commands
from datetime import time
import config.bot_tokens
import argparse
import logging
import asyncio
import config.bot_config as bot_config
import config.bot_tokens as bot_tokens

logging.basicConfig(level=logging.INFO)

bot_token = bot_tokens.PRODUCTION_TOKEN
test_mode = bot_config.TEST_MODE
if test_mode:
    logging.info("Enabling TEST mode")
    bot_token = bot_tokens.TEST_TOKEN

class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=commands.when_mentioned_or('$'), **kwargs)
        for cog in bot_config.cogs:
            try:
                self.load_extension(cog)
            except Exception as exc:
                logging.error(f"Could not load extension {cog} due to {exc.__class__.__name__}: {exc}")

    async def on_ready(self):
        logging.info('Logged on as {0} (ID: {0.id})'.format(self.user))

    async def close(self):
        for c in self.cogs:
            await self.get_cog(c).close()
        await super().close()

    def set_test_mode(self):
        for c in self.cogs:
            self.get_cog(c).set_test_mode()

intents = nextcord.Intents.all()
intents.members = True
bot = Bot(intents=intents)
if test_mode:
    bot.set_test_mode()
bot.run(bot_token)