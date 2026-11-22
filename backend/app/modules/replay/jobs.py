"""What a worker loads of `replay` (Story 10.5): its finish hook.

A Replay's last Order may be an AI player's, placed by the `ai-orders` worker, so the worker must
have `replay.service`'s hook registered (`games.service.on_game_finished`) for the Replay's
`replay` step to be recorded in that finish. `platform.jobs.TASK_MODULES` names this module, so
every worker imports it before it runs. No task is defined here yet."""

from app.modules.replay import service

__all__ = ["service"]
