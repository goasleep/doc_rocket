#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Create initial data in DB
python app/initial_data.py

# Seed built-in tools
python scripts/seed_tools.py
