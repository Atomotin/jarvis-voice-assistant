import requests
from config import BRAIN, OLLAMA_MODEL

SYSTEM = ("Ты Джарвис, вежливый ИИ-помощник Асрора из Ташкента. Обращайся 'сэр'. "
          "Отвечай по-русски, кратко: 1-2 предложения.")
URL = "http://localhost:11434/api/chat"
_history = []  # short memory of the conversation


def _ask(messages, n=120):
    r = requests.post(URL, timeout=60, json={
        "model": OLLAMA_MODEL, "stream": False, "keep_alive": -1,  # stay loaded in memory
        "options": {"num_predict": n, "temperature": 0.6}, "messages": messages})
    return r.json()["message"]["content"].strip()


def warm_up():
    """Load the model into GPU memory at start so the first answer is fast."""
    try: _ask([{"role": "user", "content": "привет"}], n=1)
    except Exception as e: print("Ollama not reachable:", e)


def think(text: str) -> str:
    if BRAIN != "local":
        return "Режим Claude подключим позже."
    _history.append({"role": "user", "content": text})
    del _history[:-6]
    try:
        answer = _ask([{"role": "system", "content": SYSTEM}] + _history)
    except Exception:
        return "Сэр, мой мозг сейчас недоступен. Проверьте, запущена ли Ollama."
    _history.append({"role": "assistant", "content": answer})
    return answer
