"""Один раз ставит кнопку «Расписание» в меню бота.
Запуск:  BOT_TOKEN=ваш_токен APP_URL=https://<логин>.github.io/<репо>/ python setup_bot.py"""
import json, os, urllib.request
token, url = os.environ["BOT_TOKEN"], os.environ["APP_URL"]
body = json.dumps({"menu_button": {"type": "web_app", "text": "📅 Расписание", "web_app": {"url": url}}}).encode()
req = urllib.request.Request(f"https://api.telegram.org/bot{token}/setChatMenuButton", body, {"Content-Type": "application/json"})
print(urllib.request.urlopen(req).read().decode())
