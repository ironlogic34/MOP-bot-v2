# Shared package integration

The shared package is implemented, not empty scaffolding.

## Available components
- UI: requester-only pagination and confirmations, standard embeds.
- Validators: text, product names, Discord IDs, amounts, permissions and hierarchy.
- Security: no-mention message defaults and best-effort credential redaction.
- Helpers: formatting, timestamps, in-process event dispatch.

## Existing integration
- Market listing names use `normalized_product_name`.
- Moderation uses shared hierarchy checks and Discord ID validation.
- General announcements and automatic replies use the no-mention policy.
- Central error reporting redacts common secret patterns.
- The bot creates a shared event bus for future activity/moderation notifications.

## Still pending
- Replace legacy `core.ui.Pages` with `shared.ui.pagination.Paginator` across commands.
- Adopt confirmations for purchases and destructive moderation actions.
- Add permission-aware module toggles and durable event/job processing.
- Expand redaction to structured log filters and exception traceback handling.
- Make interactive panels persistent across restarts where appropriate.
