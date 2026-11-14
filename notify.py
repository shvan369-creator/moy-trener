# Напоминания бота «Мой тренер». Меню и тренировки берутся из index.html.
import json, os, re, urllib.request, datetime

D = json.loads(re.search(r"const DATA = (\{.*?\});\n", open("index.html", encoding="utf-8").read(), re.S).group(1))
WEEKS = [w["name"] for w in D.get("weeks", [])] or ["База"]
START = datetime.date(2026, 11, 16)
APP = "https://shvan369-creator.github.io/moy-trener/"
# день недели (0=пн): время приёмов пищи по порядку меню
MEALS = {0: "09:00 12:00 14:00 16:45 22:30", 1: "09:00 12:00 16:00 18:30 22:45 23:15",
         2: "09:00 12:00 14:00 16:45 22:30 23:15", 3: "09:00 12:00 16:00 18:30 22:45",
         4: "09:00 11:30 12:45 15:45 22:00 23:00", 5: "10:00 13:00 15:30 18:00 20:30 22:30",
         6: "10:00 13:00 15:30 18:00 20:30"}
TRAIN = {0: ("15:00", 0), 2: ("15:00", 1), 4: ("14:00", 2)}  # напоминание за 30 мин

def send(text):
    body = {"chat_id": os.environ["CHAT_ID"], "text": text, "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": [[{"text": "Открыть приложение", "web_app": {"url": APP}}]]}}
    req = urllib.request.Request("https://api.telegram.org/bot" + os.environ["TELEGRAM_TOKEN"] + "/sendMessage",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    print(urllib.request.urlopen(req).read().decode()[:120])

def utc_slot(t):
    h, m = map(int, t.split(":"))
    x = (h * 60 + m - 183) % 1440
    return f"{x % 60} {x // 60}"

def main():
    sched = os.environ.get("SCHEDULE", "")
    if not sched:
        send("✅ Напоминания подключены! Бот будет писать перед тренировками и когда пора поесть.")
        return
    slot = " ".join(str(int(v)) for v in sched.split()[:2])
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    day = now.date() if now.hour >= 3 else now.date() - datetime.timedelta(days=1)
    dow = day.weekday()
    for i, t in enumerate(MEALS[dow].split()):
        if utc_slot(t) == slot:
            m = D["meals"][dow]["meals"][i]
            txt = f"🍽 <b>Пора поесть: {m['name'].lower()}</b>\n" + "\n".join("• " + x for x in m["items"])
            txt += f"\n\n~{m['kcal']} ккал · ~{m['p']} г белка. Отметь в приложении ✓"
            if dow in TRAIN and i == 0:
                w = D["workouts"][TRAIN[dow][1]]
                txt += f"\n\n💪 Сегодня тренировка {w['code']} — {w['title']}."
            send(txt)
    if dow in TRAIN and utc_slot(TRAIN[dow][0]) == slot:
        w = D["workouts"][TRAIN[dow][1]]
        n = (day - START).days // 7
        wk = WEEKS[0] if n < 0 else WEEKS[n % len(WEEKS)]
        send(f"💪 <b>Через 30 минут тренировка {w['code']}</b>\n{w['title'].capitalize()} · неделя «{wk}»\n"
             "Приготовь гирю, гантель, стул и полотенце, налей воды. Открой приложение и нажми «Начать тренировку».")

main()
