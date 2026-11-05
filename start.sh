#!/usr/bin/env bash
# Запуск Brifly одной командой: ./start.sh
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
python manage.py migrate
python manage.py seed_demo
echo
echo "Открывайте http://127.0.0.1:8000  (логин: demo, пароль: demo12345)"
python manage.py runserver
