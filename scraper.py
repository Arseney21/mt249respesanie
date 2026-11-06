import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://нкпт.рф/raspisanie-zanyatiy/raspisanie-nemirovicha/www/"
GROUPS_PAGE = urljoin(BASE, "bg.htm")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
PAUSE = 0.3


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    # сайт может быть в windows-1251
    if r.encoding is None or r.encoding.lower() in ("iso-8859-1", "ascii"):
        r.encoding = r.apparent_encoding or "windows-1251"
    return r.text


def get_all_groups():
    """Возвращает список (name, bg_id) с страницы bg.htm."""
    html = fetch(GROUPS_PAGE)
    soup = BeautifulSoup(html, "lxml")

    groups = {}
    # ищем все ссылки вида bgNN.htm (относительные или абсолютные)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        m = re.search(r"bg(\d+)\.htm", href, re.IGNORECASE)
        if not m:
            continue
        name = a.get_text(strip=True)
        if not name:
            continue
        # пропускаем мусорные ссылки (навигация, "назад" и т.п.)
        if len(name) < 3 or name.lower() in ("назад", "вперед", "далее"):
            continue
        bg_id = int(m.group(1))
        # дедупликация по id: если встречается несколько раз — берём первый непустой текст
        if bg_id not in groups:
            groups[bg_id] = name

    # сортируем по id, чтобы порядок был стабильным
    result = [(groups[i], i) for i in sorted(groups.keys())]
    return result


def parse_schedule(html, group_name):
    """
    Парсит расписание группы со страницы cgNN.htm.
    Возвращает структуру:
    {
      "group": "...",
      "days": [ {"date": "...", "weekday": "...", "lessons": [ {...}, ... ]}, ... ]
    }
    """
    soup = BeautifulSoup(html, "lxml")
    days = []

    # Ищем все таблицы с классом inf (по отчёту Kimi — table.inf)
    tables = soup.find_all("table", class_="inf")
    if not tables:
        # fallback: любая таблица
        tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        current_day = None
        for tr in rows:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            texts = [c.get_text(" ", strip=True) for c in cells]

            # Определяем строку-заголовок дня: обычно первая ячейка содержит дату/день недели
            # Пример: "Понедельник 04.11"
            joined = " ".join(texts)
            day_match = re.search(
                r"(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье)[^\d]*(\d{1,2}[./]\d{1,2})?",
                joined, re.IGNORECASE
            )
            if day_match and (current_day is None or len(cells) <= 2):
                if current_day is not None:
                    days.append(current_day)
                current_day = {
                    "weekday": day_match.group(1),
                    "date": day_match.group(2) or "",
                    "lessons": [],
                }
                continue

            # Строка с парой: обычно 4-6 ячеек (номер, время, предмет, кабинет, подгруппа)
            if current_day is not None and len(cells) >= 3:
                # пропускаем строки, где нет номера пары
                num = texts[0]
                if not re.match(r"^\d+$", num):
                    continue
                lesson = {
                    "num": num,
                    "time": texts[1] if len(texts) > 1 else "",
                    "subject": texts[2] if len(texts) > 2 else "",
                    "room": texts[3] if len(texts) > 3 else "",
                    "subgroup": texts[4] if len(texts) > 4 else "",
                }
                # чистим пустые поля
                lesson = {k: v for k, v in lesson.items() if v}
                current_day["lessons"].append(lesson)

        if current_day is not None:
            days.append(current_day)
            current_day = None

    # если дни не нашли через заголовки — попробуем альтернативный разбор: каждая таблица = один день
    if not days and tables:
        for table in tables:
            caption = table.find("caption")
            title = caption.get_text(" ", strip=True) if caption else ""
            m = re.search(
                r"(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота)[^\d]*(\d{1,2}[./]\d{1,2})?",
                title, re.IGNORECASE
            )
            weekday = m.group(1) if m else ""
            date = m.group(2) if m and m.group(2) else ""
            lessons = []
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                texts = [c.get_text(" ", strip=True) for c in cells]
                if len(cells) >= 3 and re.match(r"^\d+$", texts[0]):
                    lesson = {
                        "num": texts[0],
                        "time": texts[1] if len(texts) > 1 else "",
                        "subject": texts[2] if len(texts) > 2 else "",
                        "room": texts[3] if len(texts) > 3 else "",
                        "subgroup": texts[4] if len(texts) > 4 else "",
                    }
                    lesson = {k: v for k, v in lesson.items() if v}
                    lessons.append(lesson)
            if lessons:
                days.append({"weekday": weekday, "date": date, "lessons": lessons})

    return {"group": group_name, "days": days}


def main():
    print("Загружаем список групп...")
    groups = get_all_groups()
    print(f"Найдено групп: {len(groups)}")
    if len(groups) < 2:
        print("ОШИБКА: не удалось найти группы на bg.htm. Проверь вёрстку.")
        return

    schedules = {}
    for name, bg_id in groups:
        cg_url = urljoin(BASE, f"cg{bg_id}.htm")
        try:
            html = fetch(cg_url)
        except Exception as e:
            print(f"  [!] {name} (cg{bg_id}.htm) — ошибка загрузки: {e}")
            continue
        try:
            data = parse_schedule(html, name)
        except Exception as e:
            print(f"  [!] {name} — ошибка парсинга: {e}")
            continue
        schedules[name] = data
        print(f"  [ok] {name}: {len(data['days'])} дн., "
              f"{sum(len(d['lessons']) for d in data['days'])} пар")
        time.sleep(PAUSE)

    # защита: если распарсили меньше половины — не перезаписываем файл
    if len(schedules) < len(groups) / 2:
        print(f"ОШИБКА: распарсено только {len(schedules)} из {len(groups)} групп. "
              f"Файл schedule.json НЕ перезаписан.")
        return

    output = {
        "version": 2,
        "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "groups": [name for name, _ in groups],
        "schedules": schedules,
    }

    with open("docs/schedule.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Сохранено {len(schedules)} групп в docs/schedule.json")


if __name__ == "__main__":
    main()
