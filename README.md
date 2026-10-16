# MOP Bot V2

Modular, public, **multi-server** Discord bot. Initial implementation includes Moderation, General and Server Management cogs. Each server has isolated configuration and activity data.

## Run

1. Install Python 3.11 or newer.
2. Run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set your Discord bot token.
4. Enable the **Server Members**, **Message Content** and **Presence** intents in the Discord Developer Portal.
5. Run `python bot.py`.

Runtime storage is automatically created at `data/mop.sqlite3`. Never commit `.env` or runtime databases.

## Structure

- `bot.py`: lifecycle, extension loading, command registration.
- `core/database.py`: persistent per-server SQLite storage.
- `core/permissions.py`: hierarchy and staff permission checks.
- `core/errors.py`: background error handler.
- `core/ui.py`: reusable pagination.
- `modules/moderation/cogs/`: members, channels, warnings, history.
- `modules/general/cogs/`: general commands.
- `modules/server_management/cogs/`: configuration, automation, leveling, support.

## Important status

**Early implementation, not production-ready.** This PR implements a useful subset of commands. Several currently have deliberately limited functionality compared with the V2 specification. For example: mute uses Discord timeout rather than bot-managed permission restrictions; rankcard is text rather than a generated image; tickets are recorded but do not yet notify staff; the welcome command supports a text template only; warnings do not automatically escalate; and audit/history retention is incomplete. Backup, timed actions, DM appeals, role rewards, and persistent interactive panels remain to be implemented.

Discord default permissions are also enforced at runtime for implemented staff commands. Automated integration testing against a real Discord server has not yet been performed.

## Future

The universal MOP Points economy and global marketplace will be separate modules. Discord servers remain independently configured, while those later global systems will be shared across all servers.
