# Trials Bot Commands — Organizer Guide

This guide covers the slash commands that automate the full lifecycle of a Trial: from announcing
signups through weekly races to final archival. It assumes you are familiar with how Trials work
and focuses on the bot commands that replace the previously manual setup steps.

All commands are slash commands invoked with `/`. Trial management commands are under the
`/async_mod` group. Server configuration is under `/async_admin`.

---

## Quick Reference

| Command | Who Can Use | Purpose |
|---|---|---|
| `/async_admin server_config` | Admins only | Configure server-level settings required for Trials |
| `/async_mod announce_trial` | Mods/Admins | Post signup announcement and begin reaction tracking |
| `/async_mod cancel_trial` | Mods/Admins | Cancel an unstarted trial and clean up created objects |
| `/async_mod start_trial` | Organizer, Mods/Admins | Create channels, finisher role, and bot race category |
| `/async_mod start_trial_race` | Organizer, Mods/Admins | End the previous race (if any) and start the next one |
| `/async_mod end_trial` | Organizer, Mods/Admins | Mark the trial as ended and close the final race |
| `/async_mod archive_trial` | Organizer, Mods/Admins | Remove Discord channels/roles and archive the trial |

---

## Key Concepts

**Participant role** — A Discord role created when the trial is announced. Users receive this role
automatically when they react to the announcement message, and lose it when they un-react. The
participant role is how the bot tracks who is signed up and is used to auto-assign racers to each
weekly race.

**Finisher role** — A Discord role that grants access to the spoilers channel. It is assigned to a
racer automatically when they submit their time for the current race. When the next race starts, the
role is stripped from everyone, closing spoilers access until they submit again. This ensures only
racers who have finished the current week's seed can see spoiler discussion.

**Bot race category** — An internal bot construct (separate from a Discord channel category) that
holds the trial's scoring settings, extra info fields, and race history. All races created for the
trial belong to this category. The category is deactivated (but not deleted) when the trial is
archived, preserving the full race record permanently.

---

## Full Lifecycle

### Step 1 — One-Time Server Setup

> *Performed once by an admin. Skip if already configured.*

Run `/async_admin server_config`. This presents a configuration panel where you set:

- **Admin Role** and **Mod Role** — which Discord roles have admin/mod access to bot commands
- **Trials: Enabled** toggle — must be on for trial commands to work
- **Announcement Channel** — the Discord channel where trial announcements are posted
- **Trials Discord Category** — the Discord channel category under which the bot will create the
  trial's general and spoilers channels

---

### Step 2 — Announcing the Trial

> *Run by a Mod or Admin.*

Run `/async_mod announce_trial`. The bot walks you through:

1. **Select organizer** — choose the Discord member who will run this trial, or click
   **No Organizer** to leave it unassigned. The organizer is notified when minimum signups are
   reached and can run start/race/end commands on their own trial without needing a mod role.

2. **Trial details** — a form asking for:
   - **Trial Name** — used for display (e.g. `TTP Season 4 Frenzy`)
   - **Short Name** — used for channel and role names (e.g. `TTPFour-enzy`); keep it concise
   - **Short Description** — shown in the bot race category
   - **Minimum Signups** — how many signups trigger an organizer notification (leave blank to disable)
   - **Announcement Text** — the text of the signup post (omit if attaching to an existing message)

3. **Participant role name** — the bot proposes a name based on the short name. Click **Edit Name**
   to change it or **Next** to accept.

4. The bot creates the participant role, posts the announcement to the configured announcement
   channel, and begins tracking reactions. Users who react to the announcement are automatically
   assigned the participant role; users who un-react have it removed.

> **Attaching to an existing announcement:** If a signup post was already made manually, pass its
> message ID as the optional `message_id` parameter. The bot will attach to that message instead of
> posting a new one. The announcement text field is omitted from the form in this case.

---

### Step 3 — Cancelling (If Needed)

> *Run by a Mod or Admin. Only available while the trial is in Announcing state.*

Run `/async_mod cancel_trial`. If there is only one announcing trial the bot selects it
automatically; otherwise you choose from a list. A confirmation embed is shown before anything is
deleted. On confirm, the bot removes the participant role, deletes the announcement message, and
removes the trial record. This command is blocked if the trial already has any races with
submissions — use `/async_mod end_trial` and `/async_mod archive_trial` instead.

---

### Step 4 — Starting the Trial

> *Run by the organizer or a Mod/Admin. Transitions the trial from Announcing → Active.*

Run `/async_mod start_trial`. If you have permission to start multiple trials a selection prompt
appears; otherwise the bot proceeds directly. The flow:

1. **Channel names** — the bot proposes a general channel name based on the short name (e.g.
   `ttpfour-enzy`) and a spoilers channel (e.g. `ttpfour-enzy-spoilers`). Click **Edit** to adjust
   either name, then **Next** to confirm.

   - The **general channel** is visible to everyone and is where race info is posted each week.
   - The **spoilers channel** is hidden by default; access is gated by the finisher role.

2. **Finisher role name** — the bot proposes a name. Edit or accept with **Next**.

3. **Scoring type** — select how races in this trial will be scored (No Scoring, MarioKart,
   Trueskill, Par Time, or Fixed Points).

4. **Bot category settings** — review and adjust the race category settings using the toggle
   buttons. Most defaults are appropriate for Trials. Click **Confirm Settings** when done.

5. **Extra info fields** — optionally assign additional submission fields (e.g. VoD link, attempt
   count). Click **Edit Extra Info** to open the selection menu:
   - Select an existing field to add it. Fields already assigned show a ✅.
   - Selecting an assigned field removes it.
   - Choose **Create New...** to define a new field type (name, description, data type).
   - When adding a field, you are asked whether it should be **Required** or **Optional**.
   - Click **Done** when finished.

The bot then creates the general channel, spoilers channel, finisher role, and bot race category in
Discord. The trial is now **Active** and ready for races.

> **If the flow is interrupted mid-way:** The bot saves progress after each Discord object is
> created. If you run `/async_mod start_trial` again on the same trial, it will detect the partial
> state and offer two options: **Rollback Partial Start** (delete what was created and start over)
> or **Continue Setup** (resume from where it left off).

---

### Step 5 — Starting a Race

> *Run by the organizer or a Mod/Admin. Repeat each week.*

Run `/async_mod start_trial_race`. The flow:

1. **End previous race** *(if one exists)* — the bot automatically ends and scores the previous
   race before proceeding.

2. **Signup decision** — choose whether to **Close Signups** (prevent new participants from joining
   via the announcement) or **Keep Signups Open** (allow new reactions to grant the participant role
   during the race).

3. **Participant management** — review and adjust who is in the race before it is created. Three
   buttons are available:

   - **Add Racer** — opens a Discord member picker. The selected member receives the participant
     role and will be auto-assigned to the race. This works regardless of whether the added member
     has bot management permissions — the bot performs the role assignment on their behalf.
   - **Remove Racer** — presents a list of current participants. The selected member has their
     participant role removed and will not be assigned to the race.
   - **Done** — proceed to race creation.

4. **Race details** — a form asking for:
   - **Race Description** — label for this week's race (e.g. `Week 3 — Open World Keysanity`)
   - **Seed** — the seed number, link, or identifier
   - **Hash** *(optional)* — hash string for the seed

5. The bot creates the race, auto-assigns every current participant role holder, activates the race,
   posts the race info message to the general channel, and pins it there. The finisher role is
   stripped from all members at this point, resetting spoilers channel access for the new race.

Racers interact with the bot through the race info message in the general channel to submit times,
view race details, and forfeit. After submitting, they are automatically granted the finisher role
and can access the spoilers channel.

---

### Step 6 — Ending the Trial

> *Run by the organizer or a Mod/Admin. Used after the final race of the trial.*

Run `/async_mod end_trial`. A confirmation embed is shown describing what will happen. On confirm:

- The current active race is ended and scored
- The trial is marked **Ended**
- Reaction tracking stops (signups can no longer be accepted)

Channels and roles are left in place at this stage so post-trial discussion can continue in the
general and spoilers channels. The final leaderboard remains accessible.

---

### Step 7 — Archiving the Trial

> *Run by the organizer or a Mod/Admin.*

Run `/async_mod archive_trial`. The bot shows a summary of all Discord objects associated with the
trial (channels, roles, and bot category) and presents four cleanup options:

| Button | What is removed |
|---|---|
| **Category Only** | Deactivates the bot race category; leaves channels and roles untouched |
| **Remove Roles & Category** | Deletes participant and finisher roles; deactivates category |
| **Remove Channels & Category** | Deletes general and spoilers channels; deactivates category |
| **Remove All** | Deletes channels and roles; deactivates category |

The bot race category is always **deactivated** (never deleted), preserving the full race history,
submission records, and standings permanently. The trial is marked **Archived** and no further
commands can be run on it.

Dismiss the message without clicking a button to abort with no changes made.
