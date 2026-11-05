# Расписание МТ-24/9 — Telegram Mini App

- `docs/index.html` — само мини-приложение (GitHub Pages раздаёт папку `docs/`)
- `docs/schedule.json` — расписание, его обновляет `scraper.py`
- `.github/workflows/update.yml` — GitHub Actions каждые 30 минут забирает свежее расписание с сайта НКПТ
- `setup_bot.py` — разовая установка кнопки меню в боте (можно и без него, через @BotFather)

## Запуск
1. Создать публичный репозиторий на GitHub и загрузить в него эти файлы.
2. Settings → Pages → Source: «Deploy from a branch», ветка `main`, папка `/docs`.
3. Settings → Actions → General → Workflow permissions: «Read and write».
4. В @BotFather: /mybots → бот → Bot Settings → Menu Button → вставить ссылку `https://<логин>.github.io/<репо>/`.
