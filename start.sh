#!/bin/bash
export DB_PATH="/app/data/tippspiel.db"
mkdir -p /app/data
python bot/bot.py &
uvicorn web.server:app --host 0.0.0.0 --port $PORT
