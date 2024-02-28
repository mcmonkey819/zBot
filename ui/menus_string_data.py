# -*- coding: utf-8 -*-

DefaultFooter = "For more information use the commands in the Race Management Info embed. When you're done you can dismiss this message or it will dismiss itself after some time."
FirstPageEmoji = '⤴️'
LastPageEmoji = '⤵️'
NextPageEmoji = '⬇️'
PreviousPageEmoji = '⬆️'

LeaderboardEmoji = '🥇'
EditEmoji = '✏️'
DeleteEmoji = '🗑️'
CategoryEmoji = '🏷️'
RaceEmoji = '🏎️'
ExtraInfoEmoji = '📋'
HelpEmoji = '❔'
EditScoreEmoji = '📝'
SubmitRoleEmoji = '👤'
CreateRoleEmoji = '🗣️'
EditPointsEmoji = '🔢'
ToggleEmoji = '☑'
ChangeStateEmoji = '🚦'
PinEmoji = '📌'
AssignEmoji = '🫵🏽'
EditSubmissionEmoji = '🔧'
OpenRacesEmoji = '📖'
CompletedRacesEmoji = '🏁'
StatsEmoji = '📊'
ViewOtherEmoji = '👀'

EmojiList = [
    "🐱", "🐵", "🦄", "🐼",
    "🐲", "🐷", "🐭", "🐰",
    "🐮", "🐺", "🦊", "🦝",
    "🐸", "🦁", "🐹", "🐻",
    "🐻‍❄️", "🐨", "🫎", "🐯",
    "🍔", "🍟", "🍕", "🌭",
    "🍿", "🍩", "🍪", "🍫",
    "🍰", "🧁", "🍦", "🍨",
    "🍧", "🍭", "🍮", "🍯",
    "🍬", "🥧", "🍝", "🍜",
    "🎷", "🎸", "🎹", "🎺",
    "🧪", "🔬", "🔭", "📡",
    "🔨", "🪚", "🪛", "🪜",
    "🪝", "🪞", "🪟", "🪠",
    "🪡", "🪢", "🪣", "🪤",
    "🪥", "🪦", "🪧", "🪨",
    "🪩", "🪪", "🪫", "🪬",
    "🪭", "🪮", "🪯", "🪰",
    "🪱", "🪲", "🪳", "🪴",
    "🪵", "🪶", "🪷", "🪸",
    "🪹", "🪺", "🪻", "🪼",
    "🪽", "🪿", "🫀",
]

CreateEditCategoryDescription = 'Create a new category or modify an existing category.'
CreateEditRaceDescription = 'Create a new race or modify an existing race.'
CreateEditExtraInfoDescription = 'Create a new submission value or modify an existing one.'
RaceModerationHelpDescription = 'Displays detailed information about race moderation and the available commands.'

CategoryEditDescription = 'Allows you to edit the name & description of the category.'
CategoryDeleteDescription = 'Deletes the category. This will only succeed if there are no races created that use the category.'
CategoryEditScoringDescription = 'Allows you to choose a scoring method for races in this category. See the "Category Scoring" command under the Race Moderation Info embed for more information on the available methods.'
CategoryEditSubmitRoleDescription = 'Allows you to choose the role that is assigned to users when they submit a time for this category. Choosing the "None" option means no role will be assigned.'
CategoryEditCreateRoleDescription = 'Allows you to select a role to be pinged on race creation for this category. The announcement message will be editable at the time of creation. Choosing the "None" option will result in no new race ping.'
CategorySetLeaderboardChannelDescription = 'Allows you to select a channel to display the points leaderboard for this category. The leaderboard will be updated when races are completed. Choosing the "None" option will result in no leaderboard being displayed.'
CategoryEditPointsDescription = 'Allows you to manually modify the points of racers in this category. This is useful for manually awarding bonus points or correcting errors.'
CategoryAssignExtraInfoDescription = 'Allows you to assign a specific submission value to all races in this category. Already assigned values are marked with a ✅, choosing an already assigned value will unassign it from this category.'
CategoryMiscToggleDescription = 'Allows configuration of various miscellaneous category data such as leaderboard type, category visibility, required extra info, etc'

RaceEditDescription = 'Allows you to edit the core info about the race, such as the seed, hash, description and instructions.'
RaceDeleteDescription = 'Deletes the race. This will only succeed if the race is inactive and there are no submissions for the race.'
RaceChangeStateDescription = 'Allows you change the race state. Inactive state is used to set up the race. Active state will allow users to discover and submit to the race. Completed state will prevent new submissions and, if applicable, score the race.'
RacePinDescription = 'Allows you to select a a channel to pin the race info message. The message will include the core race info as well as buttons for submission, forfeit and viewing the leaderboard. Chossing "None" for channel will unpin the race info if it is already pinned.'
RaceEditSubmitRoleDescription = 'Allows you to choose the role that is assigned to users when they submit a time for this race. This is in addition to any role assigned by the race category. Choosing the "None" option means no role will be assigned.'
RaceEditLeaderboardChannelDescription = 'Allows you to select a channel to display the leaderboard for this race. The leaderboard will be updated when times are submitted. Choosing the "None" option will result in no leaderboard being displayed.'
RaceAssignExtraInfoDescription = 'Allows you to assign a specific submission value to this race. Already assigned values are marked with a ✅, choosing an already assigned value will unassign it from this race.'
RaceAssignRacerDescription = 'Allows you to assign specific racers to this race. See the "Race Assignment" command under the Race Moderation Info embed to learn more about race assignments.'
RaceEditSubmissionDescription = 'Allows you to modify a submission to this race. This is useful for correcting errors or fixing scoring errors.'
RaceMiscToggleDescription = 'Allows configuration of various miscellaneous race data such as force removing the leaderboard and specifying which extra info fields are required.'

CategoryHelpDescription = 'Displays information about creating and managing categories.'
CategoryScoringHelpDescription = 'Displays information about the available scoring types for categories.'
RaceHelpDescription = 'Displays information about creating and managing races.'
ExtraInfoHelpDescription = 'Displays information about the extra info fields and how to create and assign them.'

RacerStatsDescription = 'Displays your race stats.'
RacerOpenRacesDescription = 'Shows a list of open async races. Selecting a race from the drop down will display additional details and commands.'
RacerAssignedRacesDescription = 'Shows a list of races that have been assigned to you. Selecting a race from the drop down will display additional details and commands.'
RacerShowCategoriesDescription = 'Creates a dropdown menu with a list of categories, selecting a category will display info and additional commands.'
RacerViewOtherRacerDescription = "Shows a list of racers in the server. Selecting a racer from the drop down will display that racer's stats and a list of their completed races."
RacerShowCompletedRacesDescription = 'Shows a list of completed races. Selecting a race from th drop down will display additional information and commands. Note that completed races will not accept new submissions, but the race info and leaderboard can be viewed.'
RacerHelpDescription = 'Displays detailed help information for the other commands in this menu.'

CategoryHelpText = """
All races start with a category. Categories can be used in a number of different ways to share history and keep track of scoring.

**Category Examples**
Some servers run a weekly or monthly async of the same or similar type which would be a category, for example:  "40 Bonks Weekly", "Seed of the Week" or "Monthly Spoiler Log". In other cases, the category might be used to run a series of qualifiers, individual rounds or an entire mini-tournament like a battle royale: "Lightspeed Tournament Qualifiers", "Winter 2024 Swiss Round 2" or "Glass Cannon BR".

**Category Configuration**
Once a category has been created, there are a few additional things that can be configured for it. Categories have a scoring type, which is explained in more detail in the `Category Scoring` help command. A `create role` or `submit role` can be assigned to the category. The `create role` is a role that will be pinged when a new race announcement is made for the category. The `submit role` is a role that will be assigned to users when they submit a time for a race in this category (and removed upon creation of a new race). These are useful for managing weekly/monthly type asyncs. There is also a `leaderboard channel` that can be assigned to the category. This channel will be used to display the current category leaderboard, which will be replced/updated when races are completed. 

There is also a command available to edit individual racer's category points. This is useful for manually awarding bonus points or correcting errors, but is not intended to be the primary method for updating category points. Note that the category leaderboard will not be updated when points are manually modified, to force an update use the `Set Leaderboard Channel` command for the category and choose the same channel already set which will trigger an update. Finally there are `extra info` fields that can be assigned to the category. These are custom fields captured upon race submission, extra info is explained in more detail in the "Extra Info" help command. There is no limit to the number of categories that can be created. 

**Future Features**
A future feature may allow for categories to be grouped or tagged for easier discovery and management or marked as "inactive" to hide them from the category list. There is also currently no support for tournament management (creating brackets, randomizing matchups, etc), but there are other solutions for that which may be connected to this bot in the future (like start.gg, tourneybot.gg, etc).
"""

CategoryScoringHelpText = """
Categories have an optional scoring type that can be set by the category creator. Points are calculated per racer when a race is completed based on their placement and the scoring type. The latest point totals are stored and viewable in the category leaderboard. These are the currently available scoring types and their descriptions:

**No Scoring** 
    Disables scoring for the category. No points will be calculated on race completion.

**MarioKart** 
    Points are awarded strictly based on placement. Points are awarded to the top 15 using the following list, any submissions outside the top 15 will receive 0 points:
    [ 25, 21, 18, 15, 12, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1 ]

**Trueskill**
    Trueskill is an ELO like rating system that tries to quantify a player's skill using the Bayesian inference algorithm. Sounds fancy, but think racetime.gg points, it's like that. 
    With Trueskill scoring, the rating of each racer will be updated with every completed race. 
    The points stored for the race represent the users rating at the point of that race completion. Points stored in the category leaderboard represent the most current rating.
    You can read more about Trueskill here: https://trueskill.org/

**Par Time**
    Par time scoring uses the top 3-5 times submitted to calculate a "par" time for the race. 
    Points for the race are then calculated using the formula: (2 - (par_time / finish_time)) * 100 which should put most points in the 50-110 range.
    Points for the category are the average of par scores, dropping the bottom score if there are more than 2 races and dropping top and bottom if there are more than 3.

**Fixed Points**
    This scoring type assigns a fixed 3 points for a win and 1 point for a tie. 
    This scoring type is only intended for categories where races are 1v1, if used for larger races it will assign 3 points to the winner and zero to all other racers.
"""

RaceHelpText = """
Races are created with a category and a seed which is a freeform text field used to hold the seed number or link to randomizer seed or website. There are additional, optional fields for the race description, additional racer instructions and the seed hash (used to verify racers have the correct seed loaded in some randomizers). Once the race has been created there is some additional configuration that can be done, if desired.

**Race Configuration**
Like categories, races can have a `submit role` and a `leaderboard channel` assigned to them. The `submit role` is a role that will be assigned to users when they submit a time for the race and the leaderboard channel is used to display the current leaderboard for the race and is updated when times are submitted. These fields do not replace the category fields, but are in addition to them.

Likewise, extra info can be assigned to individual races, which will be in addition to any extra info assigned to the category. For more information about extra info fields see the "Extra Info" help command. 

The `Pin Race` command is used to post a message in the selected channel with the basic race info and buttons to get race details, submit/edit times and view the leaderboard. This message can be unpinned by selecting "None" for the channel.

**Racer Assignment**
All races are either "Open" or "Assigned". An open race is an active race that has nobody assigned to it, these races allow anyone to discover the race and submit to it while it is active. An assigned race has specific racers assigned to it, and only those racers will be able to submit times. 

Race assignment is typically used for running tournament asyncs where there are specific matchups or a specific list of people signed up, versus open races which are typically used for open community asyncs (e.g. the Go Mode Podcast biweekly seed).

**Race States**
The `Change State` command is used to change the state of the race. Races can be in one of three states: Inactive, Active or Completed. `Inactive` is the default state on creation and is used to do intial setup of the race such as editing the core info, assigning racers and setting the submit role. `Active` is used to allow users to discover and submit times to the race. `Completed` closes the race which will prevent new submissions and, if applicable, calculates points for the race and category. In general, races cannot be moved backward in state (i.e. from Active to Inactive), unless there has been no activity/submissions for the race. 

**Submission Editing**
The `Edit Submission` command is used to modify a submission or submit on behalf of another racer. The command will first prompt you to select a racer, then the submission edit menu will be displayed. If that user has previously submitted a time for the race the menu will be prepopulated with the values they entered, otherwise it will be blank. When editing a submission for an already completed race, a `Points` field will be added to the menu allowing for manual update of race points for that submission. Note that currently this will not update the category points, nor will points be recalculated for the race based on an updated submission time. Finally, if a race leaderboard channel is set, it will not be updated after editing a submission. To force a leaderboard update, use the `Set Leaderboard Channel` command and select the already set channel to force an update.
"""

ExtraInfoHelpText = """
Extra info fields are custom fields that are captured for race submissions. By default, the only information that is captured for a submission is the finish time and a comment. Often specific types of games, categories and tournaments have additional information that is useful or required to capture. For example, A Link to the Past Randomizer nearly always captures the collection rate for a seed. Certain servers may want to capture a suggestion for the next race and certain categories or tournaments may want to collect an extra piece of information like a death count for a OHKO category. 

Extra info fields can be created by race moderators. They will contain a name, description, a type and, optionally, a default value. The available types are:
   **Integer** - A whole number
   **String** - A freeform text field
   **Time** - A time in the format HH:MM:SS
   **Date/Time** - A string representing the date or date + time, typically some subset of the format 'YYYY-MM-DD HH:MM:SS`

Once an extra info field has been created, it can be assigned to a category, an individual race or the entire server. When assigned to a category, all races in that category will have the extra info field assigned on creation. Similarly, when assigned to the server the extra info field will be assigned on creation of all races in the server. When assigned to an individual race it only applies to that race. Extra info fields can be unassigned from any of the above using the assign command and selecting the already assigned field.
"""

RacerInfoHelpText = """
This help command gives an overview of racing with the bot and available commands for racers.

**Categories**
Races are created by `Race Moderators` and each race is assigned a category. Categories can be used in a number of different ways to share history and keep track of scoring. For a run down of available categories you should ask a race moderator for this server. 

Categories can optionally be assigned a scoring system, which will award points or update a rating for each completed race in the category. Examples of available scoring types are "MarioKart" style where points are awarded based on placement (e.g. 1st place gets 25 points, 2nd place gets 21 points, etc), "Par Time" scoring which uses the top 3-5 times submitted to calculate a "par" time which is compared against your finish time to calculate a score, and "Trueskill" which is an ELO like rating system where your rating is updated with every completed race. 

Using the `Show Categories` command will display a list of available categories and buttons to display the current leaderboard for each category.

**Race Types**
All races are either "Open" or "Assigned". An open race is available to anyone to race and submit times. An assigned race is an async race created for specific racers, typically used for tournament asyncs where there are specific matchups or a specific list of people signed up. Using the `Open Races` command will display a list of currently available open races and the `Assigned Races` command will show races that you have been explicitly assigned to. 

The `Completed Races` command will show races which have finishes. These races will not accept new submissions, but the leaderboard can be displayed and the race info displayed for offline racing.

**Racer Stats**
The other available commands allow you to view some stats about your racing history in this server, or view the stats of other racers.
"""

ToggleMiscDescription = """
Use the buttons below to toggle the miscelaneous settings. Some of the buttons perform a one-time action which will be described below. For fields below that toggle a value, the field name will describe the field and the text will show the current value.
    For Example:
    **🐱 - Extra Info: Collection Rate**
      Required
      
    This indicates that the button with the 🐱 emoji will toggle the `Collection Rate` extra info required field, and it is currently required.
"""

SubmissionDetailsHelpText = "Shows all of the information about the chosen submission, including the finish time, comment and any extra info fields that were captured."

def get_race_leaderboard_title(race_id):
    return f"Leaderboard for Race ID `{race_id}`"

def get_category_no_points_message(name):
    return f"There are no points for Category `{name}` Typically this means there are no completed races yet."

toggle_leaderboard_id = "toggle_leaderboard"
toggle_category_active_id = "toggle_category_active"
category_ping_assigned_id = "category_ping_assigned"
remove_category_leaderboard_id = "remove_category_leaderboard"
remove_race_leaderboard_id = "remove_race_leaderboard"