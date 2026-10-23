#!/bin/sh
set -e

# Run database migrations before starting the main process
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "Running Alembic database migrations..."
    alembic upgrade head || echo "Migrations failed or already up to date, continuing..."
fi

# Execute the CMD from Dockerfile
exec "$@"
