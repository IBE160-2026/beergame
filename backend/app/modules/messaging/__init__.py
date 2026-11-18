"""Mail delivery (AD-9, Story 3.5). The only reader of notices (`platform/notify.claim_due`) and
the only module that defers a `mail` job. No module imports `messaging` to notify: they call
`platform/notify.enqueue`, and later kinds register here in `delivery.py`. Only `ops` (the
sweep) imports `messaging.service`."""
