JARVIS - каркас (2026-11-25)
Файлы: jarvis.py (главный цикл), ears.py (микрофон+Whisper), voice.py (голос),
brain.py (мозг: Ollama/Claude), commands/ (команды), config.py (настройки).
Запуск (после установки Python 3.11 и Ollama):
  pip install -r requirements.txt
  ollama pull qwen2.5:3b
  python jarvis.py
Дальше: громкость, музыка, напоминания, погода, скриншоты, выключение, экран HUD.
