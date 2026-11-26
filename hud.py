"""Iron-Man style arc-reactor HUD: borderless, always on top, bottom-right corner.
Drag with left mouse, right-click to shut Jarvis down."""
import math, os, time, textwrap, tkinter as tk

_state = {"mode": "idle", "text": ""}
COLORS = {"idle": "#1E90FF", "listening": "#00E5FF", "thinking": "#FFB300", "speaking": "#00FFA3"}
LABELS = {"idle": "ОЖИДАНИЕ", "listening": "СЛУШАЮ", "thinking": "ДУМАЮ", "speaking": "ГОВОРЮ"}
KEY = "#010203"  # transparent colour


def set(mode: str, text: str = None):
    _state["mode"] = mode
    if text is not None:
        _state["text"] = text


def run():
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", KEY)
    root.configure(bg=KEY)
    W, H = 300, 380
    root.geometry(f"{W}x{H}+{root.winfo_screenwidth() - W - 20}+{root.winfo_screenheight() - H - 70}")
    c = tk.Canvas(root, width=W, height=H, bg=KEY, highlightthickness=0)
    c.pack()

    drag = {}
    c.bind("<Button-1>", lambda e: drag.update(x=e.x, y=e.y))
    c.bind("<B1-Motion>", lambda e: root.geometry(
        f"+{root.winfo_x() + e.x - drag['x']}+{root.winfo_y() + e.y - drag['y']}"))
    c.bind("<Button-3>", lambda e: os._exit(0))

    cx, cy = W // 2, 150

    def draw():
        t, mode = time.time(), _state["mode"]
        col = COLORS.get(mode, "#1E90FF")
        p = 1 + 0.05 * math.sin(t * 8) if mode in ("listening", "speaking") else 1
        spin = 2.5 if mode == "thinking" else 1
        c.delete("all")
        for i in range(60):  # tick ring
            a = math.radians(i * 6 + t * 10)
            r1, r2 = 132, 138 if i % 5 else 144
            c.create_line(cx + r1 * math.cos(a), cy + r1 * math.sin(a),
                          cx + r2 * math.cos(a), cy + r2 * math.sin(a), fill=col)
        for r, ext, speed, w in ((120, 250, 40, 3), (102, 120, -70, 7), (84, 200, 110, 2), (66, 80, -160, 9)):
            r *= p
            c.create_arc(cx - r, cy - r, cx + r, cy + r, start=(t * speed * spin) % 360,
                         extent=ext, style="arc", outline=col, width=w)
        c.create_oval(cx - 44, cy - 44, cx + 44, cy + 44, outline=col, width=3, fill="#06141F")
        c.create_text(cx, cy - 6, text="J.A.R.V.I.S", fill=col, font=("Consolas", 11, "bold"))
        c.create_text(cx, cy + 14, text=LABELS.get(mode, ""), fill=col, font=("Consolas", 8))
        c.create_text(cx, 300, text=time.strftime("%H:%M:%S"), fill=col, font=("Consolas", 10))
        msg = "\n".join(textwrap.wrap(_state["text"], 40)[:3])
        c.create_text(cx, 340, text=msg, fill="#BFEFFF", font=("Segoe UI", 9), justify="center")
        root.after(33, draw)

    draw()
    root.mainloop()
