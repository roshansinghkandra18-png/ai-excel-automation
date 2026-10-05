"""
Look and feel: the "Console" design - a dark side rail with the app mark and
navigation, and a light working area on the right.

Plain Tkinter only, no heavy frameworks, so it still starts quickly on older
office PCs. Rounded corners and soft edges are drawn onto a Canvas, since
Tkinter frames can only ever be square.
"""

import tkinter as tk
import tkinter.font as tkfont

# --- Palette ---------------------------------------------------------------
RAIL = "#12161F"          # dark side rail
RAIL_DEEP = "#0C0F16"     # rail edge / pressed states
RAIL_HOVER = "#1C222E"
RAIL_TEXT = "#8C97A8"
RAIL_TEXT_ON = "#FFFFFF"

ACCENT = "#2E9E86"        # calm clinical green - the one strong colour
ACCENT_HOVER = "#37B89C"
ACCENT_PRESS = "#26856F"
ACCENT_SOFT = "#E8F5F1"

CANVAS = "#F4F6F8"        # working area background
CARD = "#FFFFFF"
LINE = "#E3E8EE"
TEXT = "#171C24"
TEXT_SOFT = "#5A6675"
TEXT_FAINT = "#93A0B0"

OK = "#1F8A6D"
WARN = "#B26A00"
BAD = "#C0392B"
SELECT_BG = "#DCEEE8"     # gentle selection instead of harsh system blue


def pick_font(root):
    """Segoe UI on Windows; falls back gracefully on anything older."""
    families = set(tkfont.families(root))
    for name in ("Segoe UI", "Tahoma", "Arial"):
        if name in families:
            return name
    return "TkDefaultFont"


class Fonts:
    def __init__(self, root):
        f = pick_font(root)
        self.brand = (f, 13, "bold")
        self.h1 = (f, 20, "bold")
        self.h2 = (f, 12, "bold")
        self.label = (f, 8, "bold")
        self.body = (f, 10)
        self.body_bold = (f, 10, "bold")
        self.small = (f, 9)
        self.tiny = (f, 8)
        self.button = (f, 11, "bold")
        self.rail = (f, 9)
        self.stat = (f, 26, "bold")
        self.mono = ("Consolas", 9)


def spaced(text):
    """'ACTIVITY' -> 'A C T I V I T Y' - cheap letter-spacing for small caps."""
    return " ".join(text.upper())


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draws a rounded rectangle as a smoothed polygon."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


class RoundedPanel(tk.Frame):
    """
    A white card with rounded corners and a hairline border. The rounding is
    painted on a background canvas; content goes into `.body`.
    """

    def __init__(self, parent, bg=CARD, border=LINE, radius=10, padding=16,
                 parent_bg=CANVAS):
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0)
        self._bg, self._border, self._radius = bg, border, radius

        self.canvas = tk.Canvas(self, bg=parent_bg, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # The body must sit far enough in that the drawn corner arcs stay
        # visible - a square child frame would otherwise cover them up.
        inset = max(padding, radius - 2)
        self.body = tk.Frame(self, bg=bg)
        self.body.pack(fill="both", expand=True, padx=inset, pady=inset)

        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        self.canvas.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w > 2 and h > 2:
            round_rect(self.canvas, 1, 1, w - 1, h - 1, self._radius,
                       fill=self._bg, outline=self._border)


class RoundedButton(tk.Canvas):
    """A pill/rounded button drawn by hand, with hover and press states."""

    def __init__(self, parent, text, command, fonts, parent_bg=CANVAS,
                 fill=ACCENT, hover=ACCENT_HOVER, press=ACCENT_PRESS,
                 fg="#FFFFFF", height=52, radius=10, font=None, outline=None):
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0,
                         height=height, cursor="hand2")
        self._text = text
        self._command = command
        self._fill, self._hover, self._press = fill, hover, press
        self._fg, self._radius, self._outline = fg, radius, outline or fill
        self._font = font or fonts.button
        self._current = fill
        self._enabled = True

        self.bind("<Configure>", lambda e: self._draw(self._current))
        self.bind("<Enter>", lambda e: self._enabled and self._draw(self._hover))
        self.bind("<Leave>", lambda e: self._enabled and self._draw(self._fill))
        self.bind("<ButtonPress-1>", lambda e: self._enabled and self._draw(self._press))
        self.bind("<ButtonRelease-1>", self._release)

    def _draw(self, colour):
        self._current = colour
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2 or h <= 2:
            return
        round_rect(self, 1, 1, w - 1, h - 1, self._radius,
                   fill=colour, outline=self._outline)
        self.create_text(w / 2, h / 2, text=self._text, fill=self._fg,
                         font=self._font)

    def _release(self, event):
        if not self._enabled:
            return
        self._draw(self._hover)
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self._command()

    def set_text(self, text):
        self._text = text
        self._draw(self._current)

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "watch")
        self._draw(self._fill if enabled else self._press)


class RailItem(tk.Frame):
    """One entry in the dark side rail: a small drawn glyph plus a caption."""

    def __init__(self, parent, glyph, caption, command, fonts, active=False):
        super().__init__(parent, bg=RAIL, cursor="hand2")
        self._command = command
        self._active = active
        self._glyph = glyph

        # A slim accent bar down the left edge marks the page you're on.
        self.marker = tk.Frame(self, bg=RAIL, width=3)
        self.marker.pack(side="left", fill="y")

        stack = tk.Frame(self, bg=RAIL)
        stack.pack(side="left", fill="both", expand=True)
        self.stack = stack

        self.icon = tk.Canvas(stack, width=26, height=26, bg=RAIL,
                              highlightthickness=0, bd=0)
        self.icon.pack(pady=(12, 4))
        self.caption = tk.Label(stack, text=caption, bg=RAIL, fg=RAIL_TEXT,
                                font=fonts.tiny)
        self.caption.pack(pady=(0, 12))

        for w in (self, stack, self.icon, self.caption):
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", lambda e: self._command())

        self._paint()

    def _colour(self):
        return RAIL_TEXT_ON if self._active else RAIL_TEXT

    def _paint(self, bg=None):
        bg = bg or (RAIL_HOVER if self._active else RAIL)
        colour = self._colour()
        for w in (self, self.stack, self.icon, self.caption):
            w.configure(bg=bg)
        self.marker.configure(bg=ACCENT if self._active else bg)
        self.caption.configure(fg=colour)
        self.icon.delete("all")
        draw_glyph(self.icon, self._glyph, 26, colour)

    def _enter(self, _=None):
        self._paint(RAIL_HOVER)

    def _leave(self, _=None):
        self._paint()

    def set_active(self, active):
        self._active = active
        self._paint()


def draw_glyph(canvas, name, size, colour):
    """
    Small icons drawn with lines and shapes rather than typed as characters,
    so they look identical on every machine regardless of installed fonts.
    """
    m = size / 2
    if name == "upload":
        canvas.create_line(m, size * 0.72, m, size * 0.26, fill=colour, width=2)
        canvas.create_line(m - size * 0.16, size * 0.42, m, size * 0.24,
                           fill=colour, width=2)
        canvas.create_line(m + size * 0.16, size * 0.42, m, size * 0.24,
                           fill=colour, width=2)
        canvas.create_line(size * 0.22, size * 0.80, size * 0.78, size * 0.80,
                           fill=colour, width=2)
    elif name == "list":
        for i, y in enumerate((0.30, 0.50, 0.70)):
            canvas.create_oval(size * 0.20, size * y - 1.5, size * 0.20 + 3,
                               size * y + 1.5, fill=colour, outline=colour)
            canvas.create_line(size * 0.36, size * y, size * 0.82, size * y,
                               fill=colour, width=2)
    elif name == "folder":
        canvas.create_rectangle(size * 0.18, size * 0.34, size * 0.82, size * 0.76,
                                outline=colour, width=2)
        canvas.create_line(size * 0.18, size * 0.34, size * 0.40, size * 0.34,
                           fill=colour, width=2)
        canvas.create_line(size * 0.40, size * 0.34, size * 0.46, size * 0.26,
                           fill=colour, width=2)
        canvas.create_line(size * 0.46, size * 0.26, size * 0.62, size * 0.26,
                           fill=colour, width=2)
    elif name == "cross":
        arm, length = size * 0.22, size * 0.62
        canvas.create_rectangle(m - arm / 2, m - length / 2, m + arm / 2, m + length / 2,
                                fill=colour, outline=colour)
        canvas.create_rectangle(m - length / 2, m - arm / 2, m + length / 2, m + arm / 2,
                                fill=colour, outline=colour)
    elif name == "doc":
        canvas.create_rectangle(size * 0.26, size * 0.18, size * 0.74, size * 0.82,
                                outline=colour, width=2)
        for y in (0.38, 0.50, 0.62):
            canvas.create_line(size * 0.36, size * y, size * 0.64, size * y,
                               fill=colour, width=1)


def brand_mark(parent, size=40, bg=RAIL, disc=ACCENT, cross="#FFFFFF"):
    """The app mark: a green rounded square with a white medical cross."""
    c = tk.Canvas(parent, width=size, height=size, bg=bg,
                  highlightthickness=0, bd=0)
    round_rect(c, 1, 1, size - 1, size - 1, size * 0.28, fill=disc, outline=disc)
    draw_glyph(c, "cross", size, cross)
    return c
