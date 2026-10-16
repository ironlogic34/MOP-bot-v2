# Shared components

Actual reusable implementations, imported by bot modules:

- `ui/pagination.py`: requester-only paginated embeds.
- `ui/confirmation.py`: requester-only confirm/cancel views.
- `ui/embeds.py`: consistent safe embeds.
- `validators/text.py`: bounded strings, Discord IDs, amounts and normalized marketplace names.
- `validators/permissions.py`: server-only, staff, owner and role-hierarchy guards.
- `security/redaction.py`: redact common secrets in error logs.
- `security/mentions.py`: safe untrusted text and no-ping defaults.
- `helpers/formatting.py`: duration, timestamps, number formatting and truncation.
- `helpers/events.py`: lightweight async internal event bus.

**Caveats:** The event bus is in-process and not durable. Pagination and confirmations are not persistent across restarts. Credential redaction is best-effort; never log raw request headers or environment dumps.
