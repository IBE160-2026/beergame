#!/bin/sh
# Entry point of the backend image: bring the schema to head, then start the given command.
# Locally the schema is migrated here. With APP_ENV=production it is not, unless RUN_MIGRATIONS
# says so: on Railway only the `backend` pre-deploy command `alembic upgrade head` migrates
# (AD-24), never a worker or a restarted process.
set -e

if [ "${APP_ENV:-local}" = "production" ]; then
  default_migrations=false
else
  default_migrations=true
fi

if [ "${RUN_MIGRATIONS:-$default_migrations}" = "true" ]; then
  alembic upgrade head
fi

exec "$@"
