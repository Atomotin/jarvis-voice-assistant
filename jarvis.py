import os, re, sys, threading, traceback


class _Tee:
    """Print to the console and to jarvis.log at the same time."""
    def __init__(self, *streams): self.streams = streams
    def write(self, s):
        for st in self.streams:
            try: st.write(s); st.flush()
            except Exception: pass
    def flush(self): pass


_log = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log"), "w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _log)
sys.stderr = _Tee(sys.__stderr__, _log)

import hud
from voice import say
from ears import listen
from brain import think, warm_up
import commands

commands.SAY = say
# Whisper often mishears the name - accept close variants
WAKE = re.compile(r"\b(джа?р?ви\w*|джа?рв[еаы]с\w*|жарви\w*|жарв[еа]с\w*|дарви\w*|джерв\w*|чарви\w*|чарли\w*|ярвис\w*|jarvis\w*|jarvi\w*)[,.!?]?")


def is_stop(t: str) -> bool:
    t = t.strip(" .,!?")
    return t in ("стоп", "хватит") or any(w in t for w in ("выключись", "отключись", "пока джарвис"))


def respond(text: str) -> bool:
    """Handle one command. Returns False when Jarvis should shut down."""
    if is_stop(text):
        say("До связи, сэр.")
        return False
    hud.set("thinking", text)
    reply = commands.handle(text)
    say(reply if reply is not None else think(text))
    return True


def loop():
    warm_up()
    say("Джарвис в сети. Слушаю вас, сэр.")
    while True:
        try:
            if not step():
                break
        except Exception:
            traceback.print_exc()
            hud.set("idle", "Ошибка, перезапускаю слух...")
    os._exit(0)


def step() -> bool:
    """One listen/answer cycle. Returns False to shut down."""
    hud.set("idle")
    heard = listen(wait=30)
    m = WAKE.search(heard)
    if not m:
        if commands.is_direct(heard):   # "открой стим", "громче" - no name needed
            return respond(heard)
        return True
    rest = heard[m.end():].strip(" ,.!?")
    if len(rest) > 2:                    # "Джарвис, сколько время" in one phrase
        return respond(rest)
    say("Да, сэр?")
    text = listen(wait=6)
    return respond(text) if text else True


if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    hud.run()  # HUD must own the main thread (tkinter)
