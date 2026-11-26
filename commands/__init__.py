import ctypes, datetime, glob, os, re, subprocess, threading, urllib.parse, webbrowser
import requests
from config import CITY

SAY = print  # jarvis.py replaces this with voice.say (used by reminders/alarms)

# ---------- apps & sites ----------
APPS = {
    "стим": "steam://open/main", "steam": "steam://open/main",
    "дискорд": "discord", "телеграм": "telegram", "браузер": "chrome", "хром": "chrome",
    "яндекс": "yandex", "блокнот": "notepad", "калькулятор": "calc",
    "проводник": "explorer", "параметры": "ms-settings:", "настройки": "ms-settings:",
    "диспетчер задач": "taskmgr", "эпик": "epic games", "валорант": "valorant",
    "лига": "league of legends", "спотифай": "spotify", "ворд": "word", "эксель": "excel",
}
SITES = {"ютуб": "https://youtube.com", "fiverr": "https://www.fiverr.com/inbox",
         "файвер": "https://www.fiverr.com/inbox", "фрилансер": "https://www.freelancer.com/messages",
         "гитхаб": "https://github.com", "почт": "https://mail.google.com"}
_TR = dict(zip("абвгдеёзийклмнопрстуфхцыэ", "abvgdeeziiklmnoprstufhcye"))
_TR.update({"ж": "zh", "ч": "ch", "ш": "sh", "щ": "sch", "ю": "yu", "я": "ya", "ъ": "", "ь": ""})
_MENU = [os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
         os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs")]

# commands that work without saying "Джарвис"
DIRECT = ("откро", "открой", "запусти", "включи", "выключи звук", "найди", "поищи", "загугли",
          "громче", "тише", "прибавь", "убавь", "громкость", "звук на", "пауза", "продолжи",
          "следующ", "предыдущ", "скриншот", "сделай скриншот", "погода", "какая погода",
          "напомни", "поставь будильник", "будильник", "разбуди", "заблокируй")


def is_direct(text: str) -> bool:
    return text.strip(" .,!?").startswith(DIRECT)


def _shortcut(name):
    keys = {name, "".join(_TR.get(c, c) for c in name)}
    for root in _MENU:
        for lnk in glob.glob(os.path.join(root, "**", "*.lnk"), recursive=True):
            if any(k and k in os.path.basename(lnk).lower() for k in keys):
                return lnk


def _open(target, known):
    if ":" in target:
        os.startfile(target); return True
    lnk = _shortcut(target)
    if lnk:
        os.startfile(lnk); return True
    if known:
        subprocess.Popen(f'start "" {target}', shell=True); return True
    return False


# ---------- helpers ----------
WORDNUM = {"одну": 1, "одна": 1, "один": 1, "две": 2, "два": 2, "три": 3, "четыре": 4, "пять": 5,
           "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "пятнадцать": 15,
           "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "сто": 100}


def _num(s, default=None):
    m = re.search(r"\d+", s)
    if m:
        return int(m.group())
    for w, n in WORDNUM.items():
        if re.search(rf"\b{w}\b", s):
            return n
    return default


def _key(code, times=1):
    for _ in range(times):
        ctypes.windll.user32.keybd_event(code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(code, 0, 2, 0)


VOL_UP, VOL_DOWN, MUTE, PLAY, NEXT, PREV = 0xAF, 0xAE, 0xAD, 0xB3, 0xB0, 0xB1


# ---------- features ----------
def _volume(t):
    if "выключи звук" in t or "без звука" in t or "включи звук" in t:
        _key(MUTE); return "Готово"
    n = _num(t)
    if n is not None and ("громкость" in t or "звук на" in t):
        _key(VOL_DOWN, 50); _key(VOL_UP, min(n, 100) // 2)
        return f"Громкость {n} процентов"
    if any(w in t for w in ("громче", "прибавь")):
        _key(VOL_UP, 5); return "Громче"
    if any(w in t for w in ("тише", "убавь")):
        _key(VOL_DOWN, 5); return "Тише"


def _music(t):
    if t.startswith(("пауза", "продолжи")) or "на паузу" in t:
        _key(PLAY); return "Готово"
    if "следующ" in t:
        _key(NEXT); return "Следующий трек"
    if "предыдущ" in t:
        _key(PREV); return "Предыдущий трек"
    if "включи музыку" in t:
        webbrowser.open("https://music.youtube.com"); return "Включаю музыку"
    m = re.search(r"включи (?:песню|трек|клип) (.+)", t)
    if m:
        q = m.group(1)
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
        return "Ищу " + q


EN_RU = {"smoky haze": "дымка", "haze": "дымка", "mist": "туман", "fog": "туман", "smoke": "смог",
         "partly cloudy": "переменная облачность", "cloudy": "облачно", "overcast": "пасмурно",
         "sunny": "солнечно", "clear": "ясно", "light rain": "небольшой дождь", "rain": "дождь",
         "snow": "снег", "dust": "пыль"}


def _weather(t):
    if "погод" not in t:
        return
    m = re.search(r"погод\w* в ([\w-]+)", t)
    city = m.group(1) if m else CITY
    try:
        j = requests.get(f"https://wttr.in/{urllib.parse.quote(city)}?format=j1&lang=ru", timeout=8).json()
        cur = j["current_condition"][0]
        desc = requests.get(f"https://wttr.in/{urllib.parse.quote(city)}?format=%C&lang=ru", timeout=8).text.strip().lower()
        for en, ru in EN_RU.items():
            desc = desc.replace(en, ru)
        today = j["weather"][0]
        return (f"Сейчас {cur['temp_C']} градусов, ощущается как {cur['FeelsLikeC']}, {desc}. "
                f"Сегодня от {today['mintempC']} до {today['maxtempC']}.")
    except Exception:
        return "Сэр, не удалось получить погоду. Проверьте интернет."


def _later(seconds, fn):
    th = threading.Timer(seconds, fn)
    th.daemon = True
    th.start()


UNITS = {"секунд": (1, "секунд"), "минут": (60, "минут"), "час": (3600, "часов"), "полчаса": (60, "минут")}


def _plural(n, word):
    forms = {"секунд": ("секунду", "секунды", "секунд"), "минут": ("минуту", "минуты", "минут"),
             "часов": ("час", "часа", "часов")}[word]
    if n % 10 == 1 and n % 100 != 11: return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14: return forms[1]
    return forms[2]


def _reminder(t):
    m = re.search(r"через\s+(?:(\S+)\s+)?(полчаса|секунд|минут|час)\w*\s*(.*)", t)
    if "напомни" in t and m:
        unit = m.group(2)
        n = 30 if unit == "полчаса" else _num(m.group(1) or "", 1)
        mult, word = UNITS[unit]
        what = m.group(3).strip(" .,!?") or t.split("напомни", 1)[1].split("через")[0].strip(" .,!?")
        _later(n * mult, lambda: SAY(f"Сэр, напоминаю: {what}" if what else "Сэр, время вышло."))
        return f"Хорошо, напомню через {n} {_plural(n, word)}"
    if any(w in t for w in ("будильник", "разбуди")):
        m = re.search(r"(\d{1,2})(?:[:.\s](\d{2}))?", t)
        if not m:
            return "На какое время поставить будильник, сэр?"
        h, mi = int(m.group(1)) % 24, int(m.group(2) or 0)
        now = datetime.datetime.now()
        at = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if at <= now:
            at += datetime.timedelta(days=1)

        def ring():
            for _ in range(3):
                SAY(f"Сэр, подъём! Уже {h}:{mi:02d}.")
        _later((at - now).total_seconds(), ring)
        return f"Будильник на {h}:{mi:02d}. Не выключайте меня и ноутбук."


def _screenshot(t):
    if "скриншот" not in t and "снимок экрана" not in t:
        return
    import pyautogui
    folder = os.path.join(os.path.expanduser("~"), "Pictures", "Jarvis")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, datetime.datetime.now().strftime("screen_%Y-%m-%d_%H-%M-%S.png"))
    pyautogui.screenshot(path)
    return "Скриншот сохранён в папку Изображения, Джарвис"


def _power(t):
    if "отмени" in t and ("выключ" in t or "перезагруз" in t):
        subprocess.call("shutdown /a", shell=True); return "Отменено"
    if "выключи компьютер" in t or "выключи ноутбук" in t:
        subprocess.call("shutdown /s /t 60", shell=True)
        return "Выключаю через минуту. Чтобы отменить, скажите: Джарвис, отмени выключение."
    if "перезагрузи" in t:
        subprocess.call("shutdown /r /t 60", shell=True)
        return "Перезагрузка через минуту. Чтобы отменить, скажите: Джарвис, отмени перезагрузку."
    if "заблокируй" in t:
        ctypes.windll.user32.LockWorkStation(); return "Блокирую"
    if "спящий режим" in t or "усыпи" in t:
        SAY("Перехожу в спящий режим")
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return ""


def handle(text: str):
    """Return a reply if a built-in command matched, else None (goes to the brain)."""
    t = text.strip(" .,!?")
    if ("время" in t and "напомни" not in t) or "который час" in t:
        return "Сейчас " + datetime.datetime.now().strftime("%H:%M")
    for feature in (_weather, _reminder, _volume, _music, _power, _screenshot):
        r = feature(t)
        if r is not None:
            return r
    for name, url in SITES.items():
        if name in t:
            webbrowser.open(url); return "Открываю"
    for verb in ("откройте", "открою", "открой", "запустите", "запусти", "включи"):
        if verb in t:
            what = t.split(verb, 1)[1].strip(" .,!?")
            for name, target in APPS.items():
                if name in what:
                    _open(target, True); return f"Запускаю {name}"
            if what and _open(what, False):
                return f"Запускаю {what}"
            return f"Не нашёл программу {what}, сэр."
    for verb in ("найди", "поищи", "загугли"):
        if verb in t:
            q = t.split(verb, 1)[1].strip()
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(q))
            return "Ищу " + q
    return None
