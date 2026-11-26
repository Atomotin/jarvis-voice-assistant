import os, sys, glob, time
import numpy as np, sounddevice as sd
import hud
from config import WHISPER_MODEL, LANGUAGE

# Windows: let ctranslate2 find the CUDA DLLs installed by the nvidia-* pip packages
for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
    os.add_dll_directory(d)
    os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]

from faster_whisper import WhisperModel

RATE = 16000
BLOCK = 1600  # 0.1 s
HINT = "Джарвис, сколько время? Открой ютуб. Открой телеграм. Найди погода в Ташкенте. Стоп."

try:
    _model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="int8_float16")
    print("Whisper:", WHISPER_MODEL, "on GPU")
except Exception as e:
    print("Whisper: GPU failed, using CPU ->", e)
    _model = WhisperModel("small", device="cpu", compute_type="int8")


def _calibrate() -> float:
    """Measure room noise once and set the speech threshold above it."""
    noise = sd.rec(int(1.0 * RATE), samplerate=RATE, channels=1, dtype="float32")
    sd.wait()
    level = float(np.sqrt(np.mean(noise ** 2)))
    thr = max(0.008, level * 3)
    print(f"Mic noise {level:.4f} -> threshold {thr:.4f}")
    return thr

_THRESHOLD = _calibrate()


def listen(wait: float = 8, max_len: float = 10, silence: float = 0.7) -> str:
    """Wait up to `wait` s for speech, record until `silence` s of quiet, then transcribe."""
    chunks, speaking, quiet, started, peak = [], False, 0.0, time.time(), 0.0
    pre = []  # keep 0.3 s before speech starts so the first syllable isn't cut
    with sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK) as s:
        while True:
            block, _ = s.read(BLOCK)
            rms = float(np.sqrt(np.mean(block ** 2)))
            peak = max(peak, rms)
            if not speaking:
                pre = (pre + [block])[-3:]
                if rms > _THRESHOLD:
                    speaking, chunks = True, list(pre)
                    hud.set("listening")
                elif time.time() - started > wait:
                    print(f"(quiet: loudest {peak:.4f}, need {_THRESHOLD:.4f})")
                    return ""
                continue
            chunks.append(block)
            quiet = quiet + 0.1 if rms < _THRESHOLD else 0.0
            if quiet >= silence or len(chunks) * 0.1 >= max_len:
                break
    hud.set("thinking")
    audio = np.concatenate(chunks).flatten()
    segments, _ = _model.transcribe(audio, language=LANGUAGE, vad_filter=True,
                                    initial_prompt=HINT, beam_size=1)
    text = " ".join(s.text for s in segments).strip().lower()
    if text:
        print("YOU:", text)
    return text
