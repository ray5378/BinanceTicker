"""桌面常驻实时价格信息栏 (tkinter)

半透明深色无边框窗口，默认贴桌面右下角，支持鼠标拖拽移动。
每条行情一行，涨绿跌红，实时刷新。
"""
import tkinter as tk

UP_COLOR = "#0ecb81"
DOWN_COLOR = "#f6465d"
BG_COLOR = "#18181a"
TEXT_COLOR = "#f8f8f8"
ALPHA = 0.88


class InfoBar:
    def __init__(self, on_detail=None):
        self.bg = BG_COLOR
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", ALPHA)
        self.root.configure(bg=BG_COLOR)

        self.frame = tk.Frame(self.root, bg=BG_COLOR)
        self.frame.pack(fill="both", expand=True, padx=12, pady=6)
        self._rows = []

        self._bind_drag(self.frame)
        self._bind_drag(self.root)

        self._move_to_default()
        if on_detail:
            self.frame.bind("<Double-Button-1>", lambda e: on_detail())

    def _bind_drag(self, widget):
        widget.bind("<Button-1>", self._drag_start)
        widget.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event):
        self._drag_off = (event.x_root - self.root.winfo_x(),
                          event.y_root - self.root.winfo_y())

    def _drag_move(self, event):
        x = event.x_root - self._drag_off[0]
        y = event.y_root - self._drag_off[1]
        self.root.geometry(f"+{x}+{y}")

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

    def _move_to_default(self):
        left, top, right, bottom = self._work_area()
        self.root.update_idletasks()
        x = right - self.root.winfo_reqwidth() - 16
        y = bottom - self.root.winfo_reqheight() - 16
        self.root.geometry(f"+{max(left, x)}+{max(top, y)}")
        self._kept_geom = False

    def update_rows(self, rows):
        """rows: [(文本, 前景色) 或 None 行, ...] 每条行情一行。"""
        for i in range(len(self._rows)):
            if i < len(rows):
                self._rows[i].destroy()
        need = len(rows)
        if need < len(self._rows):
            for label in self._rows[need:]:
                label.destroy()
        self._rows = self._rows[:need]
        for i, row in enumerate(rows):
            text, color = (row or (None, None))
            if i < len(self._rows):
                label = self._rows[i]
                label.configure(text=text, fg=color or TEXT_COLOR)
            else:
                label = tk.Label(self.frame, text=text, bg=BG_COLOR,
                                 fg=color or TEXT_COLOR, anchor="w",
                                 justify="left",
                                 font=("Microsoft YaHei UI", 10))
                label.pack(fill="x", anchor="w")
                self._bind_drag(label)
                self._rows.append(label)
        if not self._kept_geom:
            self.root.update_idletasks()
            if self.root.winfo_width() < self.root.winfo_reqwidth():
                w = max(self.root.winfo_reqwidth(), 220)
                self.root.geometry(f"{w}x{self.root.winfo_reqheight()}")

    def run(self, refresh_cb, interval_ms=1000):
        def _tick():
            if self.root.state() == "normal":
                refresh_cb(self)
            self.root.after(interval_ms, _tick)
        self._tick_fn = _tick
        self.root.after(interval_ms, _tick)
        self.root.mainloop()

    def call_after(self, ms, fn, *args):
        self.root.after(ms, fn, *args)

    def stop(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass