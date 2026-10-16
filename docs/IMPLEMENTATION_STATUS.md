# Initial implementation status

This PR starts the three requested modules. It does **not** implement the entire finalized command specification.

## Moderation
Implemented initial commands: ban, unban, kick, mute, unmute, nickname, role, slowmode, lock, unlock, cleanup, nsfw, sfw, warn, warnhistory, modhistory, stat, history, mkdstat.

Pending or requiring expansion: audit, botclear, denyperm, hide, lockdown; timed bans, warnings escalation, message-history retention, reversible layered locks, bot-managed mutes, date-based cleanup, richer permission management, channel access kick.

## General
Initial commands: ping, userinfo, bug, echo. Bug is currently a status response; background errors go to application logs. Echo supports one channel only.

## Server Management
Initial commands: customise, welcome, invite, autoresponder, autoreact, level, rankcard, ticket, logs.

Pending or requiring expansion: alias, autorole, backup, bump, language/translate, leave, live, appeal; richer welcome cards, graphical rankcards, full ticket workflow, importable automation rules, settings UI, moderation log channel routing, anti-spam scoring.

## Shared architecture
Working: independent guild settings, SQLite schema creation, shared audit log, basic hierarchy checks, centralized command error handler, extension separation.

Next: migrations, permission engine expansion, background queues, persistent views, per-guild module toggles, structured health monitoring, test suite, development/production separation, SQLite-to-PostgreSQL abstraction.

Do not advertise this branch as a complete 83-command release.


## Second batch: remaining modules
The previously empty module folders now contain working initial implementations and are loaded by `bot.py`:
- **Utility:** /timer, /notify, /pin, /unpin, /img2gif. /bumpreminder pending. Reminder delivery is currently at-most-once, and reports are stored but lack a staff dashboard.
- **Music:** /music, /play, /pause, /resume, /skip, /queue, /nowplaying, /volume, /loop, /shuffle, /stop, /lyrics, /fm, /lastfm. Last.fm integration is a status stub; scrobbling and statistics pending. Direct audio is **disabled until MUSIC_ALLOWED_HOSTS is configured**. FFmpeg required. Voice session hardening and richer controls pending.
- **Economy:** /economy, /balance, /daily, /work, /deposit, /withdraw, /transfer, /leaderboard, /market, /inventory, /buy, /sell, /additem. Global points, inventory and market purchase/sell use SQLite transactions. /addbalance, /resetbalance, /credit, /loan and listing management pending. Listing products are virtual; redemption and eligibility controls pending.
- **Help:** /help category selector and compact descriptions.
- **Background errors:** loop-level handler and cog event error monitoring. Persistent structured error records, redaction and recovery pending.

**Security:** Set `MUSIC_ALLOWED_HOSTS` only to domains you trust for direct audio streaming. An allowlist alone does not fully protect against DNS rebinding or redirects; audio source handling needs additional hardening before public deployment. Real secrets belong only in local `.env`, not Git.

## Current completion pass (October 2026)
This pass adds a **restart-persistent moderation sanction scheduler**, timed ban cancellation, warning-threshold escalation (default three warnings and a 24-hour ban), a per-server /audit viewer, a sanitized persistent error-record repository, and an actual /bug error viewer. Sanction tests cover replacement, cancellation, duration validation, and guild isolation.

**Not a complete implementation.** Remaining specification gaps include advanced moderation commands and retention, comprehensive server management (backup, appeals, ticket workflows, autoroles), full general command behavior, utility delivery semantics, economy administration/credit/loan, permission-aware help, and durable background infrastructure. Music remains deferred. The shared package still lacks durable events and persistent UI. No live Discord integration tests have been run.

A green compile/import/unit-test workflow does not establish production readiness.
