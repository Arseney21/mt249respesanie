#!/usr/bin/env python3
"""Скачивает расписание группы с сайта НКПТ и сохраняет в docs/schedule.json."""
import json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

BASE = "https://xn--j1afhm.xn--p1ai/raspisanie-zanyatiy/raspisanie-nemirovicha/www/"
GROUP = {"name": "МТ-24/9", "page": "cg38.htm"}   # cg38 = «Неделя» для МТ-24/9
BELLS = {  # с сайта: /raspisanie-zvonkov/raspisanie-zvonkov.php (5-я пара — по аналогии)
    "1": ["08:30", "10:05"], "2": ["10:15", "11:50"], "3": ["12:30", "14:05"],
    "4": ["14:15", "15:50"], "5": ["16:00", "17:35"],
}
OUT = "docs/schedule.json"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MT24-MiniApp"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_cell(td, subgroup=None):
    lessons, cur = [], None
    for a in td.find_all("a"):
        cls = (a.get("class") or [""])[0]
        txt = a.get_text(" ", strip=True)
        if cls == "z1":
            m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", txt)
            cur = {"subject": m.group(1) if m else txt, "type": m.group(2) if m else "",
                   "room": "", "teacher": "", "subgroup": subgroup}
            lessons.append(cur)
        elif cur and cls == "z2":
            cur["room"] = txt
        elif cur and cls == "z3":
            cur["teacher"] = txt
    return lessons


def parse(html):
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="inf")
    if not table:
        raise RuntimeError("Таблица расписания не найдена — возможно, изменилась вёрстка сайта")
    days, day = [], None
    for tr in table.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue
        first = tds[0]
        m = re.search(r"(\d{2}\.\d{2}\.\d{4})", first.get_text(" ", strip=True))
        if m and first.get("rowspan"):
            d = datetime.strptime(m.group(1), "%d.%m.%Y").date()
            label = first.get_text("|", strip=True).split("|")[-1]  # «Пн-1»
            day = {"date": d.isoformat(), "label": label, "week": label.split("-")[-1], "pairs": []}
            days.append(day)
            tds = tds[1:]
        if day is None or not tds:
            continue
        num = tds[0].get_text(strip=True)
        if not num.isdigit():
            continue
        cells = tds[1:]
        lessons = []
        if len(cells) == 1:
            lessons = parse_cell(cells[0])
        else:  # разные подгруппы
            for i, c in enumerate(cells, 1):
                lessons += parse_cell(c, subgroup=i)
        day["pairs"].append({"num": int(num), "time": BELLS.get(num), "lessons": lessons})
    upd = re.search(r"Обновлено:\s*([\d.]+\s*в\s*[\d:]+)", soup.get_text(" ", strip=True))
    return days, (upd.group(1) if upd else None)


def main():
    html = fetch(BASE + GROUP["page"])
    days, updated = parse(html)
    if not days:
        sys.exit("Пустое расписание — файл не перезаписан")
    data = {
        "group": GROUP["name"],
        "source": BASE + GROUP["page"],
        "siteUpdated": updated,
        "fetchedAt": datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="minutes"),
        "bells": BELLS,
        "days": days,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    n = sum(len(p["lessons"]) for d in days for p in d["pairs"])
    print(f"OK: {len(days)} дней, {n} занятий, сайт обновлён {updated}")


if __name__ == "__main__":
    main()
