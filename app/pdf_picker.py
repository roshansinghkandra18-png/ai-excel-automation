"""
The app's own PDF chooser: a styled list of recent PDFs, so staff never see
the plain Windows file dialog. A 'Browse elsewhere' link is kept as a
fallback for a PDF stored somewhere unusual.
"""

import os
import time
import tkinter as tk
from tkinter import filedialog

import theme as th

# Where PDFs usually live. Checked in order; all existing ones are scanned.
def default_search_folders():
    home = os.path.expanduser("~")
    return [
        os.path.join(home, "Downloads"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
    ]


def recent_pdfs(folders, limit=40):
    found = []
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        try:
            for name in os.listdir(folder):
                if name.lower().endswith(".pdf") and not name.startswith("~"):
                    full = os.path.join(folder, name)
                    try:
                        found.append((os.path.getmtime(full), full))
                    except OSError:
                        pass
        except OSError:
            pass
    found.sort(reverse=True)
    return [path for _, path in found[:limit]]


def humanise(when):
    days = (time.time() - when) / 86400
    if days < 1:
        return "Today"
    if days < 2:
        return "Yesterday"
    if days < 7:
        return f"{int(days)} days ago"
    return time.strftime("%d %b %Y", time.localtime(when))


class PdfRow(tk.Frame):
    """One selectable PDF in the list."""

    def __init__(self, parent, path, on_pick, fonts):
        super().__init__(parent, bg=th.CARD, cursor="hand2")
        self._path = path
        self._on_pick = on_pick

        inner = tk.Frame(self, bg=th.CARD)
        inner.pack(fill="x", padx=14, pady=9)

        self.icon = tk.Canvas(inner, width=22, height=22, bg=th.CARD,
                              highlightthickness=0, bd=0)
        th.draw_glyph(self.icon, "doc", 22, th.ACCENT)
        self.icon.pack(side="left")

        text = tk.Frame(inner, bg=th.CARD)
        text.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self.name = tk.Label(text, text=os.path.basename(path), bg=th.CARD,
                             fg=th.TEXT, font=fonts.body_bold, anchor="w")
        self.name.pack(anchor="w")

        try:
            when = humanise(os.path.getmtime(path))
        except OSError:
            when = ""
        self.meta = tk.Label(text, text=f"{when}   ·   {os.path.dirname(path)}",
                             bg=th.CARD, fg=th.TEXT_FAINT, font=fonts.tiny,
                             anchor="w")
        self.meta.pack(anchor="w")

        self._widgets = [self, inner, self.icon, text, self.name, self.meta]
        for w in self._widgets:
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", lambda e: self._on_pick(self._path))

    def _paint(self, bg):
        for w in self._widgets:
            w.configure(bg=bg)

    def _enter(self, _=None):
        self._paint(th.ACCENT_SOFT)

    def _leave(self, _=None):
        self._paint(th.CARD)


class PdfPicker(tk.Frame):
    """The scrollable list of recent PDFs plus a browse-elsewhere fallback."""

    def __init__(self, parent, on_pick, fonts, bg=th.CANVAS):
        super().__init__(parent, bg=bg)
        self.on_pick = on_pick
        self.fonts = fonts

        head = tk.Frame(self, bg=bg)
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text=th.spaced("Recent PDFs"), bg=bg, fg=th.TEXT_SOFT,
                 font=fonts.label).pack(side="left")
        tk.Label(head, text="Refresh", bg=bg, fg=th.ACCENT, font=fonts.small,
                 cursor="hand2").pack(side="right")
        head.winfo_children()[-1].bind("<Button-1>", lambda e: self.refresh())

        self.panel = th.RoundedPanel(self, padding=8, parent_bg=bg)
        self.panel.pack(fill="both", expand=True)

        holder = tk.Frame(self.panel.body, bg=th.CARD)
        holder.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(holder, bg=th.CARD, highlightthickness=0, bd=0)
        self.scroll = tk.Scrollbar(holder, orient="vertical", command=self.canvas.yview,
                                   width=10, bd=0, highlightthickness=0,
                                   troughcolor=th.CARD)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.rows = tk.Frame(self.canvas, bg=th.CARD)
        self._window = self.canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.rows.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._wheel)

        browse = tk.Label(self, text="PDF saved somewhere else?  Browse…", bg=bg,
                          fg=th.ACCENT, font=fonts.small, cursor="hand2")
        browse.pack(anchor="w", pady=(10, 0))
        browse.bind("<Button-1>", lambda e: self.browse())

        self.refresh()

    def _wheel(self, event):
        try:
            if self.canvas.winfo_ismapped():
                self.canvas.yview_scroll(int(-event.delta / 120), "units")
        except tk.TclError:
            pass

    def refresh(self):
        for child in self.rows.winfo_children():
            child.destroy()

        paths = recent_pdfs(default_search_folders())
        if not paths:
            tk.Label(self.rows, text="No PDFs found in Downloads, Desktop or Documents.",
                     bg=th.CARD, fg=th.TEXT_FAINT, font=self.fonts.small).pack(
                pady=26)
            return

        for i, path in enumerate(paths):
            if i:
                tk.Frame(self.rows, bg=th.LINE, height=1).pack(fill="x", padx=14)
            PdfRow(self.rows, path, self.on_pick, self.fonts).pack(fill="x")

    def browse(self):
        path = filedialog.askopenfilename(title="Select today's PDF",
                                          filetypes=[("PDF files", "*.pdf")])
        if path:
            self.on_pick(path)
