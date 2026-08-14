"""桌面常驻实时价格信息栏 (tkinter)

半透明深色无边框窗口，默认贴桌面右下角，支持鼠标拖拽移动。
每条行情一行，涨绿跌红，实时刷新。
"""
import tkinter as tk
import tkinter.font as tkfont

UP_COLOR = "#0ecb81"
DOWN_COLOR = "#f6465d"
BG_COLOR = "#18181a"
TEXT_COLOR = "#f8f8f8"
ALPHA = 0.88
MARGIN = 16
FRAME_PADX = 12
TEXT_PAD = 4
MIN_WIDTH = 260
FONT_FAMILY = "Microsoft YaHei UI"
FONT_SIZE = 10


class InfoBar:
    def __init__(self, on_detail=None):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", ALPHA)
        self.root.configure(bg=BG_COLOR)

        self.frame = tk.Frame(self.root, bg=BG_COLOR)
        self.frame.pack(fill="both", expand=True,
                        padx=FRAME_PADX, pady=6)
        self._labels = []
        self._user_moved = False
        self._font = tkfont.Font(family=FONT_FAMILY, size=FONT_SIZE)

        self._bind_drag(self.frame)
        self._bind_drag(self.root)

        if on_detail:
            self.frame.bind("<Double-Button-1>", lambda e: on_detail())

        self.update_rows([])

    # ---- 拖拽 ----
    def _bind_drag(self, widget):
        widget.bind("<Button-1>", self._drag_start)
        widget.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event):
        self._user_moved = True
        self._drag_off = (event.x_root - self.root.winfo_x(),
                          event.y_root - self.root.winfo_y())

    def _drag_move(self, event):
        x = event.x_root - self._drag_off[0]
        y = event.y_root - self._drag_off[1]
        self.root.geometry(f"+{max(0, x)}+{max(0, y)}")

    # ---- 定位 ----
    def _work_area(self):
        try:
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0,
                                                       ctypes.byref(rect), 0)
            return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            return (0, 0, self.root.winfo_screenwidth(),
                    self.root.winfo_screenheight())

    def _measure_width(self, rows):
        """用字体度量最长行的像素宽度，含边距与缓冲。"""
        max_text = 0
        for text, _color in rows:
            w = self._font.measure(text or "")
            if w > max_text:
                max_text = w
        return max(max_text + FRAME_PADX * 2 + TEXT_PAD, MIN_WIDTH)

    def _place_bottom_right(self, width):
        """贴到桌面右下角，窗口宽度为测量值。用户拖拽过则保留其位置。"""
        self.root.update_idletasks()
        if self._user_moved:
            self.root.geometry(f"{width}x{self.root.winfo_reqheight()}")
            self.root.update_idletasks()
            return
        left, top, right, bottom = self._work_area()
        h = self.root.winfo_reqheight()
        x = max(left, right - width - MARGIN)
        y = max(top, bottom - h - MARGIN)
        self.root.geometry(f"{width}x{h}+{x}+{y}")
        self.root.update_idletasks()

    # ---- 内容 ----
    def update_rows(self, rows):
        """rows: [(文本, 前景色) 或 None, ...] 每条行情一行。全部重建。"""
        for label in self._labels:
            label.destroy()
        self._labels = []

        for text, color in rows:
            label = tk.Label(self.frame, text=text or "",
                             bg=BG_COLOR, fg=color or TEXT_COLOR,
                             anchor="w", justify="left",
                             font=(FONT_FAMILY, FONT_SIZE))
            label.pack(fill="x", anchor="w")
            self._bind_drag(label)
            self._labels.append(label)

        self._place_bottom_right(self._measure_width(rows))

    # ---- 生命周期 ----
    def run(self, refresh_cb, interval_ms=1000):
        def _tick():
            try:
                refresh_cb(self)
            except Exception:
                pass
            self.root.after(interval_ms, _tick)

        self.root.after(0, _tick)
        self.root.mainloop()

    def call_after(self, ms, fn, *args):
        self.root.after(ms, fn, *args)

    def stop(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass