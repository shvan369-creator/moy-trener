# Ответы бота «Мой тренер» на сообщения. Запускается GitHub Actions каждые 5 минут.
import json, os, re, time, datetime, urllib.request

D = json.loads(re.search(r"const DATA = (\{.*?\});\n", open("index.html", encoding="utf-8").read(), re.S).group(1))
API = "https://api.telegram.org/bot" + os.environ["TELEGRAM_TOKEN"] + "/"
CHAT = int(os.environ["CHAT_ID"])
START = datetime.date(*map(int, D.get("start", "2026-11-16").split("-")))
TRAIN = {0: 0, 2: 1, 4: 2}
TRAIN_TIME = "10:00"
DN = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
DNV = ["в понедельник", "во вторник", "в среду", "в четверг", "в пятницу", "в субботу", "в воскресенье"]
MEALS = {0: "08:00 13:30 16:30 11:15 22:30", 1: "09:00 12:00 16:00 18:30 22:45 23:15",
         2: "08:00 13:30 16:30 11:15 22:30 23:15", 3: "09:00 12:00 16:00 18:30 22:45",
         4: "08:00 13:30 15:30 11:15 22:00 23:00", 5: "10:00 13:00 15:30 18:00 20:30 22:30",
         6: "10:00 13:00 15:30 18:00 20:30"}
KB = {"keyboard": [[{"text": "🏋️ Тренировка сегодня"}, {"text": "🍽 Что поесть сейчас"}],
                   [{"text": "📋 Меню на сегодня"}, {"text": "📅 Неделя"}]],
      "resize_keyboard": True, "is_persistent": True}
HELP = ("Привет! Я твой бот-тренер 💪\n\nСпрашивай меня обычными словами или жми кнопки внизу:\n"
        "• «во сколько тренировка?»\n• «что мне поесть?»\n• «что я сегодня должен съесть?»\n"
        "• «что завтра?» / «меню на завтра»\n• «неделя»\n\n"
        "Отвечаю в течение нескольких минут. Техника и таймер — в приложении, кнопка «Тренер».")

def call(method, **p):
    req = urllib.request.Request(API + method, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=3)

def week(d):
    n = (d - START).days // 7
    return 0 if n < 0 else n % len(D["weeks"])

def adj(sets, wi):
    m = re.match(r"(\d+)\s*×\s*(\d+)(?:–(\d+))?\s*(сек)?", sets)
    if not m:
        return sets
    W = D["weeks"][wi]
    n = max(2, min(5, int(m[1]) + W["sets"]))
    lo, hi, timed = int(m[2]), int(m[3] or m[2]), bool(m[4])
    if timed:
        if W["mode"] == "tech": hi, lo = lo, max(20, lo - 15)
        if W["mode"] == "int": lo, hi = lo + 15, hi + 15
    elif W["mode"] == "tech":
        if lo == hi: lo = hi = max(5, lo - 5)
        else: hi = min(hi, lo + 2)
    reps = str(lo) if lo == hi else f"{lo}–{hi}"
    side = " на каждую руку" if "руку" in sets else (" на каждую ногу" if "ногу" in sets else "")
    return f"{n} × {reps}{' сек' if timed else ''}{side}"

def training(d, word="Сегодня"):
    dow = d.weekday()
    if dow not in TRAIN:
        k = next(x for x in range(1, 8) if (dow + x) % 7 in TRAIN)
        nd = d + datetime.timedelta(days=k)
        w = D["workouts"][TRAIN[nd.weekday()]]
        return (f"{word} силовой нет — день танцев и восстановления 💃\n\n"
                f"Следующая тренировка {DNV[nd.weekday()]}, {nd.day:02d}.{nd.month:02d}, в {TRAIN_TIME} — "
                f"{w['code']} ({w['title']}).")
    w, wi = D["workouts"][TRAIN[dow]], week(d)
    W = D["weeks"][wi]
    t = (f"💪 <b>{word} тренировка {w['code']} в {TRAIN_TIME}</b>\n{w['title'].capitalize()} · неделя «{W['name']}»\n"
         f"{W['text']}\n\n<b>Мобильность, 8–10 мин:</b>\n")
    t += "\n".join(f"• {m['name']} — {m['dose']}" for m in w["mob"])
    t += "\n\n<b>Основная часть:</b>\n" + "\n".join(
        f"{i}. {e['name']} — {adj(e['sets'], wi)}" + (f"\n    🏋 {e['weight']}" if e.get("weight") else "")
        for i, e in enumerate(w["ex"], 1))
    t += "\n\nОтдых между подходами 60–90 сек. Техника и таймер — в приложении."
    return t

def meals_of(d):
    dow = d.weekday()
    ms, ts = D["meals"][dow]["meals"], MEALS[dow].split()
    return sorted(((ts[i], ms[i]) for i in range(len(ms))), key=lambda x: x[0])

def fmt(tm, m):
    return (f"<b>{tm} — {m['name']}</b>\n" + "\n".join("• " + x for x in m["items"]) +
            f"\n~{m['kcal']} ккал · ~{m['p']} г белка")

def menu(d, word="сегодня"):
    lst = meals_of(d)
    k, p = sum(m["kcal"] for _, m in lst), sum(m["p"] for _, m in lst)
    return f"📋 <b>Меню на {word}</b> (~{k} ккал, ~{p} г белка)\n\n" + "\n\n".join(fmt(*x) for x in lst)

def eat_now(n):
    d, cur = n.date(), n.strftime("%H:%M")
    lst = meals_of(d)
    past = [x for x in lst if x[0] <= cur]
    fut = [x for x in lst if x[0] > cur]
    if past:
        h, mi = map(int, past[-1][0].split(":"))
        ago = (n - datetime.datetime.combine(d, datetime.time(h, mi))).total_seconds() / 60
        if ago <= 90:
            t = "🍽 Сейчас по плану:\n\n" + fmt(*past[-1])
            if fut:
                t += f"\n\nСледующий приём в {fut[0][0]} — {fut[0][1]['name'].lower()}."
            return t
    if fut:
        return "🍽 Следующий приём пищи:\n\n" + fmt(*fut[0])
    first = meals_of(d + datetime.timedelta(days=1))[0]
    return ("На сегодня всё по плану 👍 Если голоден — творог, кефир или банан.\n\nЗавтра первый приём:\n\n"
            + fmt(*first))

def weekplan(d):
    mon = d - datetime.timedelta(days=d.weekday())
    t = f"📅 <b>Неделя «{D['weeks'][week(d)]['name']}»</b>\n"
    for i in range(7):
        x = mon + datetime.timedelta(days=i)
        if i in TRAIN:
            w = D["workouts"][TRAIN[i]]
            s = f"{TRAIN_TIME} — тренировка {w['code']} ({w['title']})"
        else:
            s = "танцы и восстановление"
        t += f"\n{'👉 ' if x == d else ''}<b>{DN[i]} {x.day:02d}.{x.month:02d}</b> — {s}"
    return t

FOOD = ("поест", "съест", "куша", "еда", "еду", "меню", "питан", "завтрак", "обед", "ужин", "перекус", "голод", "есть")
FULL = ("меню", "сегодня", "весь", "за день", "питан", "план")
TRAINW = ("трен", "заняти", "упражн", "во сколько", "когда", "качат")

def answer(text):
    t, n = text.lower(), now()
    d = n.date()
    strong_food = any(k in t for k in FOOD if k != "есть")
    if "завтра" in t:
        nd = d + datetime.timedelta(days=1)
        if strong_food:
            return menu(nd, "завтра")
        return training(nd, "Завтра") + "\n\nМеню на завтра — спроси «меню на завтра»."
    if "недел" in t or "расписан" in t:
        return weekplan(d)
    if strong_food:
        return menu(d) if any(k in t for k in FULL) else eat_now(n)
    if any(k in t for k in TRAINW):
        return training(d)
    if "есть" in t:
        return eat_now(n)
    return HELP

def main():
    if os.environ.get("EVENT") == "workflow_dispatch":
        call("sendMessage", chat_id=CHAT, text=HELP, reply_markup=KB)
    end, off = time.time() + 270, None
    while time.time() < end:
        p = {"timeout": max(1, min(25, int(end - time.time()))), "allowed_updates": ["message"]}
        if off:
            p["offset"] = off
        try:
            res = call("getUpdates", **p).get("result", [])
        except Exception as e:
            print("getUpdates error", e); time.sleep(5); continue
        for u in res:
            off = u["update_id"] + 1
            m = u.get("message") or {}
            if m.get("chat", {}).get("id") != CHAT or "text" not in m:
                continue
            txt = m["text"]
            try:
                out = HELP if txt.startswith(("/start", "/help")) else answer(txt)
            except Exception as e:
                print("answer error", e); out = "Что-то пошло не так 🙈 Попробуй спросить иначе."
            call("sendMessage", chat_id=CHAT, text=out, parse_mode="HTML", reply_markup=KB)
    if off:
        call("getUpdates", offset=off, timeout=0)

if __name__ == "__main__":
    main()
