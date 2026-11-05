@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv ( py -3 -m venv .venv || python -m venv .venv )
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python manage.py migrate
python manage.py seed_demo
echo.
echo Открывайте http://127.0.0.1:8000  (логин: demo, пароль: demo12345)
python manage.py runserver
