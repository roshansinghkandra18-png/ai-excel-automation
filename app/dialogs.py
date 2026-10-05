"""
Pop-up messages drawn in the app's own style, so nothing ever falls back to
a plain grey Windows dialog box.
"""

import tkinter as tk
import theme as th

INFO = "info"
WARN = "warn"
DANGER = "danger"

# Set once by the main window so pop-ups carry the app icon too.
ICON_PATH = None

_ACCENTS = {INFO: th.ACCENT, WARN: th.WARN, DANGER: th.BAD}


class _Modal(tk.Toplevel):
    def __init__(self, parent, fonts, title, message, kind,
                 confirm_text=None, cancel_text=None, width=520):
        super().__init__(parent)
        self.result = False
        self.withdraw()

        self.overrideredirect(False)
        self.title(title)
        if ICON_PATH:
            try:
                self.iconbitmap(ICON_PATH)  # match the main window
            except Exception:
                pass
        self.configure(bg=th.CANVAS)
        self.resizable(False, False)
        self.transient(parent)

        accent = _ACCENTS.get(kind, th.ACCENT)

        # Slim coloured band across the top signals what kind of message it is.
        tk.Frame(self, bg=accent, height=4).pack(fill="x")

        body = tk.Frame(self, bg=th.CANVAS)
        body.pack(fill="both", expand=True, padx=26, pady=22)

        tk.Label(body, text=title, bg=th.CANVAS, fg=th.TEXT, font=fonts.h2,
                 anchor="w", justify="left").pack(anchor="w")
        tk.Label(body, text=message, bg=th.CANVAS, fg=th.TEXT_SOFT,
                 font=fonts.body, anchor="w", justify="left",
                 wraplength=width - 60).pack(anchor="w", pady=(10, 0))

        buttons = tk.Frame(body, bg=th.CANVAS)
        buttons.pack(anchor="e", pady=(20, 0))

        if cancel_text:
            cancel = th.RoundedButton(
                buttons, cancel_text, self._cancel, fonts, parent_bg=th.CANVAS,
                fill=th.CANVAS, hover=th.LINE, press=th.LINE, fg=th.TEXT_SOFT,
                height=40, radius=8, outline=th.LINE, font=fonts.small)
            cancel.configure(width=120)
            cancel.pack(side="left", padx=(0, 10))

        ok = th.RoundedButton(
            buttons, confirm_text or "OK", self._confirm, fonts,
            parent_bg=th.CANVAS, fill=accent,
            hover=th.ACCENT_HOVER if accent == th.ACCENT else accent,
            press=accent, height=40, radius=8, font=fonts.small)
        ok.configure(width=150 if confirm_text else 110)
        ok.pack(side="left")

        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._confirm())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.update_idletasks()
        self._centre_on(parent)
        self.deiconify()
        self.grab_set()
        self.focus_force()

    def _centre_on(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x, y = px + (pw - w) // 2, py + (ph - h) // 3
        except tk.TclError:
            x = y = 200
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


def alert(parent, fonts, title, message, kind=INFO):
    """A single-button message. Blocks until dismissed."""
    dlg = _Modal(parent, fonts, title, message, kind)
    parent.wait_window(dlg)


def confirm(parent, fonts, title, message, confirm_text, cancel_text="Cancel",
            kind=WARN):
    """Two-button question. Returns True only if the confirm button was pressed."""
    dlg = _Modal(parent, fonts, title, message, kind,
                 confirm_text=confirm_text, cancel_text=cancel_text)
    parent.wait_window(dlg)
    return dlg.result
