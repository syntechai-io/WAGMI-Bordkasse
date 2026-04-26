#!/bin/bash
set -e

if [ -f requirements.txt ]; then
  pip install --quiet --disable-pip-version-check -r requirements.txt
fi

if [ -f alembic.ini ] && [ -d migrations/versions ] && [ -n "$DATABASE_URL" ]; then
  alembic upgrade head
fi
