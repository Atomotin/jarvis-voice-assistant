import asyncio, hashlib, os, tempfile, threading
import edge_tts, pygame
import hud
from config import VOICE

pygame.mixer.init()
_lock = threading.Lock()
_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(_CACHE, exist_ok=True)


def _synth(text: str, path: str):
    """Generate speech into a temp file, then move it into place (no half-written files)."""
    tmp = path + ".part"
    asyncio.run(edge_tts.Communicate(text, VOICE, rate="+10%").save(tmp))
    if os.path.getsize(tmp) < 1000:
        os.remove(tmp)
        raise RuntimeError("empty speech file")
    os.replace(tmp, path)


def _play(path: str):
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(30)
    pygame.mixer.music.unload()


def say(text: str):
    if not text:
        return
    print("JARVIS:", text)
    with _lock:  # reminders may speak from another thread
        hud.set("speaking", text)
        key = hashlib.md5((VOICE + text).encode()).hexdigest() + ".mp3"
        short = len(text) <= 60  # short phrases ("Да, сэр?") are cached on disk
        path = os.path.join(_CACHE if short else tempfile.gettempdir(), key)
        for attempt in (1, 2):
            try:
                if not os.path.exists(path):
                    _synth(text, path)
                _play(path)
                break
            except Exception as e:  # corrupt cache or network hiccup: rebuild once, never crash
                try: os.remove(path)
                except OSError: pass
                if attempt == 2:
                    print("(voice error:", e, ")")
        if not short:
            try: os.remove(path)
            except OSError: pass
        hud.set("idle")
