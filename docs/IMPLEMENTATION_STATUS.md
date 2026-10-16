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
