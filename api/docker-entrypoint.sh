#!/bin/sh
# Local entry point: bring the schema to head, then start the given command.
# On Railway, migrations run as the api pre-deploy command instead (AD-24),
# and RUN_MIGRATIONS=false skips them here.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi

exec "$@"
