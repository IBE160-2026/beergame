"""The `mail` queue's tasks (AD-9), run by `worker-batch`. Arguments are ids only.

- `messaging.claim_notice(notice_id)`: deferred by `platform/notify.enqueue` with the notice, so
  an `immediate` notice leaves without waiting for the sweep.
- `messaging.send_mail(delivery_id)`: deferred with each delivery; idempotent.
"""

import uuid

from app.modules.messaging import service
from app.platform import jobs, notify

__all__ = ["claim_notice", "send_mail"]


@jobs.app.task(name=notify.CLAIM_TASK, queue=jobs.MAIL)
async def claim_notice(notice_id: str) -> None:
    await service.claim_notice(uuid.UUID(notice_id), service.utcnow())


@jobs.app.task(name=service.SEND_MAIL, queue=jobs.MAIL)
async def send_mail(delivery_id: str) -> None:
    await service.send(uuid.UUID(delivery_id))
