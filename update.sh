#!/bin/bash
cd "$(dirname "$0")"
./venv/bin/python scraper.py >> logs/cron.log 2>&1
./venv/bin/python build_site.py >> logs/cron.log 2>&1
