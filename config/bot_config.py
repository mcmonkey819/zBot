# Controls whether the bot will start in test mode
TEST_MODE = True

# Path to the production database file
PRODUCTION_DB = "AsyncRaceProd.db"

# Path to the production database file
TEST_DB = "AsyncRaceTest.db"

# These are the coolest guys (no gender assumed). The user IDs of the users who are authorized to use the really sensitive features like text_talk which allows the user to talk as the bot
CoolestGuyIds = [ 178293242045923329 ]

# This is the list of cogs to be loaded when the bot is started up
cogs = [ 'cogs.async_races' ]