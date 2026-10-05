"""
Daily Measurement Excel Filer
------------------------------
Drop in a PDF and it reads the dictated entries and adds them to the right
month's tab of your single Excel record. Nothing already saved is ever
changed - only new rows are added. Anything the program can't confidently
understand is listed for you to fix by hand; it never guesses.
"""

import os
import sys
import time
import tkinter as tk
from tkinter import filedialog

import config
import pdf_reader
import parser as pdf_parser
import excel_writer
import history
import dialogs
import theme as th
from pdf_picker import PdfPicker

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

APP_TITLE = "Daily Measurement Excel Filer"


def resource_path(name):
    """Finds bundled files inside the .exe, and works when run as a script too."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


class App:
    def __init__(self, root):
        self.root = root
        self.fonts = th.Fonts(root)
        self.records_folder = config.get_records_folder()
        self.page = "today"

        root.title(APP_TITLE)
        root.configure(bg=th.CANVAS)
        root.minsize(940, 620)
        self._centre(1060, 700)
        self._set_icon()

        shell = tk.Frame(root, bg=th.CANVAS)
        shell.pack(fill="both", expand=True)

        self._build_rail(shell)
        self.stage = tk.Frame(shell, bg=th.CANVAS)
        self.stage.pack(side="left", fill="both", expand=True)

        self.pages = {}
        self._build_today_page()
        self._build_activity_page()
        self._build_settings_page()
        self._enable_drop()
        self.show("today")

    # --- window chrome ----------------------------------------------------
    def _centre(self, w, h):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{max((sw - w) // 2, 0)}+{max((sh - h) // 3, 0)}")

    def _set_icon(self):
        try:
            path = resource_path("app_icon.ico")
            self.root.iconbitmap(path)
            dialogs.ICON_PATH = path  # so pop-ups carry it too
        except Exception:
            pass  # an icon is nice to have, never worth crashing over

    # --- side rail --------------------------------------------------------
    def _build_rail(self, parent):
        rail = tk.Frame(parent, bg=th.RAIL, width=92)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)

        th.brand_mark(rail, size=40).pack(pady=(22, 6))
        tk.Label(rail, text="LEDGER", bg=th.RAIL, fg=th.RAIL_TEXT_ON,
                 font=self.fonts.tiny).pack()

        tk.Frame(rail, bg=th.RAIL_DEEP, height=1).pack(fill="x", pady=18, padx=16)

        self.rail_items = {}
        for key, glyph, caption in (
            ("today", "upload", "Today"),
            ("activity", "list", "Activity"),
            ("settings", "folder", "Settings"),
        ):
            item = th.RailItem(rail, glyph, caption,
                               lambda k=key: self.show(k), self.fonts)
            item.pack(fill="x")
            self.rail_items[key] = item

        tk.Label(rail, text="v2", bg=th.RAIL, fg=th.RAIL_TEXT,
                 font=self.fonts.tiny).pack(side="bottom", pady=14)

    def show(self, key):
        self.page = key
        for name, frame in self.pages.items():
            frame.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        for name, item in self.rail_items.items():
            item.set_active(name == key)

    # --- page: today ------------------------------------------------------
    def _build_today_page(self):
        page = tk.Frame(self.stage, bg=th.CANVAS)
        self.pages["today"] = page

        wrap = tk.Frame(page, bg=th.CANVAS)
        wrap.pack(fill="both", expand=True, padx=30, pady=26)

        tk.Label(wrap, text="Today", bg=th.CANVAS, fg=th.TEXT,
                 font=self.fonts.h1).pack(anchor="w")
        self.today_sub = tk.Label(wrap, text=time.strftime("%A %d %B %Y"),
                                  bg=th.CANVAS, fg=th.TEXT_SOFT, font=self.fonts.body)
        self.today_sub.pack(anchor="w", pady=(2, 18))

        # Drop zone / primary action
        self.drop_panel = th.RoundedPanel(wrap, padding=20)
        self.drop_panel.pack(fill="x")
        inner = tk.Frame(self.drop_panel.body, bg=th.CARD)
        inner.pack(fill="x")

        self.drop_icon = tk.Canvas(inner, width=34, height=34, bg=th.CARD,
                                   highlightthickness=0, bd=0)
        th.draw_glyph(self.drop_icon, "upload", 34, th.ACCENT)
        self.drop_icon.pack(side="left")

        texts = tk.Frame(inner, bg=th.CARD)
        texts.pack(side="left", padx=(16, 0), fill="x", expand=True)
        self.drop_title = tk.Label(
            texts,
            text="Drag today's PDF here" if DND_AVAILABLE else "Add today's PDF",
            bg=th.CARD, fg=th.TEXT, font=self.fonts.h2, anchor="w")
        self.drop_title.pack(anchor="w")
        self.drop_hint = tk.Label(
            texts, text="or pick one from the list below", bg=th.CARD,
            fg=th.TEXT_FAINT, font=self.fonts.small, anchor="w")
        self.drop_hint.pack(anchor="w")

        self.browse_btn = th.RoundedButton(inner, "Browse…", self._browse, self.fonts,
                                           parent_bg=th.CARD, height=40, radius=8)
        self.browse_btn.configure(width=120)
        self.browse_btn.pack(side="right")

        # Stat row
        stats = tk.Frame(wrap, bg=th.CANVAS)
        stats.pack(fill="x", pady=(16, 0))
        for i in range(3):
            stats.columnconfigure(i, weight=1, uniform="s")
        self.tiles = {}
        for i, (key, caption) in enumerate(
                (("added", "Rows added"), ("flagged", "Needs checking"),
                 ("tab", "Month tab"))):
            panel = th.RoundedPanel(stats, padding=18)
            panel.grid(row=0, column=i, sticky="nsew",
                       padx=(0 if i == 0 else 7, 0 if i == 2 else 7))
            box = tk.Frame(panel.body, bg=th.CARD)
            box.pack(fill="both", expand=True)
            value = tk.Label(box, text="—", bg=th.CARD,
                             fg=th.ACCENT if key == "added" else th.TEXT,
                             font=self.fonts.stat)
            value.pack(anchor="w")
            tk.Label(box, text=th.spaced(caption), bg=th.CARD, fg=th.TEXT_FAINT,
                     font=self.fonts.label).pack(anchor="w", pady=(2, 0))
            self.tiles[key] = value

        # Recent PDFs
        self.picker = PdfPicker(wrap, self._handle_pdf, self.fonts)
        self.picker.pack(fill="both", expand=True, pady=(20, 0))

    # --- page: activity ---------------------------------------------------
    def _build_activity_page(self):
        page = tk.Frame(self.stage, bg=th.CANVAS)
        self.pages["activity"] = page

        wrap = tk.Frame(page, bg=th.CANVAS)
        wrap.pack(fill="both", expand=True, padx=30, pady=26)

        tk.Label(wrap, text="Activity", bg=th.CANVAS, fg=th.TEXT,
                 font=self.fonts.h1).pack(anchor="w")
        tk.Label(wrap, text="Exactly what happened on the last run",
                 bg=th.CANVAS, fg=th.TEXT_SOFT, font=self.fonts.body).pack(
            anchor="w", pady=(2, 18))

        panel = th.RoundedPanel(wrap, padding=10)
        panel.pack(fill="both", expand=True)
        holder = tk.Frame(panel.body, bg=th.CARD)
        holder.pack(fill="both", expand=True)

        self.log = tk.Text(
            holder, wrap="word", bd=0, highlightthickness=0, bg=th.CARD,
            fg=th.TEXT, font=self.fonts.mono, padx=16, pady=14,
            spacing1=1, spacing3=3, cursor="arrow",
            selectbackground=th.SELECT_BG, selectforeground=th.TEXT,
            inactiveselectbackground=th.SELECT_BG,
        )
        scroll = tk.Scrollbar(holder, command=self.log.yview, width=10, bd=0,
                              highlightthickness=0, troughcolor=th.CARD)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        mono = self.fonts.mono[0]
        self.log.tag_configure("ok", foreground=th.OK, font=(mono, 9, "bold"))
        self.log.tag_configure("err", foreground=th.BAD, font=(mono, 9, "bold"))
        self.log.tag_configure("warn", foreground=th.WARN, font=(mono, 9, "bold"))
        self.log.tag_configure("muted", foreground=th.TEXT_SOFT)
        self.log.tag_configure("head", foreground=th.TEXT, font=(mono, 9, "bold"))
        self.log.configure(state="disabled")

        self._show_intro()

    # --- page: settings ---------------------------------------------------
    def _build_settings_page(self):
        page = tk.Frame(self.stage, bg=th.CANVAS)
        self.pages["settings"] = page

        wrap = tk.Frame(page, bg=th.CANVAS)
        wrap.pack(fill="both", expand=True, padx=30, pady=26)

        tk.Label(wrap, text="Settings", bg=th.CANVAS, fg=th.TEXT,
                 font=self.fonts.h1).pack(anchor="w")
        tk.Label(wrap, text="Where your Excel record is kept", bg=th.CANVAS,
                 fg=th.TEXT_SOFT, font=self.fonts.body).pack(anchor="w", pady=(2, 18))

        panel = th.RoundedPanel(wrap, padding=20)
        panel.pack(fill="x")
        box = tk.Frame(panel.body, bg=th.CARD)
        box.pack(fill="x")

        left = tk.Frame(box, bg=th.CARD)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=th.spaced("Save location"), bg=th.CARD,
                 fg=th.TEXT_FAINT, font=self.fonts.label).pack(anchor="w")
        self.location_label = tk.Label(left, text="", bg=th.CARD, fg=th.TEXT,
                                       font=self.fonts.body, anchor="w",
                                       justify="left", wraplength=560)
        self.location_label.pack(anchor="w", pady=(6, 0))
        tk.Label(left, text=f"One file, {excel_writer.WORKBOOK_NAME}, "
                            f"with a tab for every month.",
                 bg=th.CARD, fg=th.TEXT_FAINT, font=self.fonts.small,
                 anchor="w").pack(anchor="w", pady=(6, 0))

        change = th.RoundedButton(box, "Change", self.choose_records_folder,
                                  self.fonts, parent_bg=th.CARD, height=40, radius=8)
        change.configure(width=110)
        change.pack(side="right", padx=(16, 0))

        note = th.RoundedPanel(wrap, padding=20)
        note.pack(fill="x", pady=(14, 0))
        nb = tk.Frame(note.body, bg=th.CARD)
        nb.pack(fill="x")
        tk.Label(nb, text=th.spaced("How it works"), bg=th.CARD, fg=th.TEXT_FAINT,
                 font=self.fonts.label).pack(anchor="w")
        for line in (
            "Each day's PDF adds new rows to that month's tab.",
            "A new month automatically gets its own tab.",
            "Nothing already saved is ever changed or overwritten.",
            "A backup copy is kept alongside the program on every run.",
        ):
            tk.Label(nb, text="•  " + line, bg=th.CARD, fg=th.TEXT_SOFT,
                     font=self.fonts.small, anchor="w").pack(anchor="w", pady=(6, 0))

        self._refresh_location()

    # --- drag and drop ----------------------------------------------------
    def _enable_drop(self):
        if not DND_AVAILABLE:
            return
        try:
            for widget in (self.drop_panel, self.drop_panel.body, self.drop_title,
                           self.drop_hint, self.drop_icon):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop)
                widget.dnd_bind("<<DropEnter>>", self._drop_enter)
                widget.dnd_bind("<<DropLeave>>", self._drop_leave)
        except Exception:
            pass

    def _drop_enter(self, _=None):
        self.drop_title.configure(fg=th.ACCENT)
        self.drop_hint.configure(text="Release to add it")
        return "copy"

    def _drop_leave(self, _=None):
        self.drop_title.configure(fg=th.TEXT)
        self.drop_hint.configure(text="or pick one from the list below")

    def _on_drop(self, event):
        self._drop_leave()
        raw = (event.data or "").strip()
        path = raw[1:-1] if raw.startswith("{") and raw.endswith("}") else raw.split()[0]
        if not path.lower().endswith(".pdf"):
            dialogs.alert(self.root, self.fonts, "That isn't a PDF",
                          "Please drop a PDF file.", dialogs.WARN)
            return
        self._handle_pdf(path)

    # --- helpers ----------------------------------------------------------
    def _refresh_location(self):
        if self.records_folder:
            self.location_label.configure(text=self.records_folder, fg=th.TEXT)
        else:
            self.location_label.configure(
                text="Not chosen yet — click Change to pick a folder.", fg=th.WARN)

    def _write(self, parts):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        for text, tag in parts:
            self.log.insert(tk.END, text + "\n", tag or ())
        self.log.configure(state="disabled")
        self.log.see("1.0")

    def _show_intro(self):
        self._write([
            ("Ready.", "ok"),
            ("", None),
            ("1.  Check the save location under Settings.", "muted"),
            ("2.  Drag today's PDF in, or pick it from the list.", "muted"),
            ("3.  Come back here to see exactly what was added.", "muted"),
            ("", None),
            ("Nothing already saved is ever changed — new rows are only added.", "muted"),
        ])

    def _set_tiles(self, added="—", flagged="—", tab="—"):
        self.tiles["added"].configure(text=str(added))
        self.tiles["flagged"].configure(text=str(flagged))
        self.tiles["tab"].configure(
            text=str(tab), font=(self.fonts.stat[0], 16, "bold")
            if tab != "—" else self.fonts.stat)

    # --- actions ----------------------------------------------------------
    def choose_records_folder(self):
        path = filedialog.askdirectory(title="Where should the Excel record be kept?")
        if not path:
            return
        config.set_records_folder(path)
        self.records_folder = path
        self._refresh_location()

    def _browse(self):
        path = filedialog.askopenfilename(title="Select today's PDF",
                                          filetypes=[("PDF files", "*.pdf")])
        if path:
            self._handle_pdf(path)

    def _handle_pdf(self, pdf_path):
        if not self.records_folder:
            dialogs.alert(
                self.root, self.fonts, "Choose a folder first",
                "Please pick where the Excel record should be kept, over on the "
                "Settings page.", dialogs.WARN)
            self.show("settings")
            return
        if not os.path.isdir(self.records_folder):
            dialogs.alert(self.root, self.fonts, "Folder not found",
                          f"Could not find:\n{self.records_folder}", dialogs.DANGER)
            return

        if not self._duplicate_check(pdf_path):
            return

        self.drop_title.configure(text="Working…")
        self.root.update_idletasks()
        try:
            self._run(pdf_path)
        finally:
            self.drop_title.configure(
                text="Drag today's PDF here" if DND_AVAILABLE else "Add today's PDF")
            self.picker.refresh()

    def _duplicate_check(self, pdf_path):
        """
        Warns if this exact PDF has been filed before. Returns False only if
        the user decides not to go ahead.
        """
        try:
            self._fingerprint = history.fingerprint(pdf_path)
        except OSError:
            self._fingerprint = None
            return True

        seen = history.previous_entry(self.records_folder, self._fingerprint)
        if not seen:
            return True

        return dialogs.confirm(
            self.root, self.fonts,
            "This PDF has already been added",
            f"'{seen.get('file', 'It')}' was filed on {seen.get('filed_on', 'an earlier date')} "
            f"— {seen.get('rows', '?')} row(s) into the {seen.get('tab', '?')} tab.\n\n"
            f"Adding it again will put those same patients into the record a second time.\n\n"
            f"Only continue if you genuinely mean to.",
            confirm_text="Add it again anyway",
            cancel_text="Don't add",
        )

    def _run(self, pdf_path):
        self._set_tiles()
        self.show("activity")
        self.root.update_idletasks()

        try:
            text = pdf_reader.extract_text(pdf_path)
        except Exception as e:
            self._write([("Could not read that PDF.", "err"), ("", None), (str(e), "muted")])
            return

        if not text.strip():
            self._write([
                ("No text was found in that PDF.", "err"), ("", None),
                ("If the PDF is a photo or a scan, the text can't be read from it.", "muted"),
            ])
            return

        parsed = pdf_parser.parse_pdf_text(text)
        out = [(os.path.basename(pdf_path), "head")]

        if parsed.date_value is None:
            out += [
                ("", None), ("Stopped — nothing was saved.", "err"), ("", None),
                (f"The date could not be understood (it read: \"{parsed.date_raw_text or ''}\").",
                 "muted"),
                ("Every row needs a date, so nothing was written rather than guess one.", "muted"),
                ("Fix the date line in the PDF and try again.", "muted"),
            ]
            self._write(out)
            return

        out.append((parsed.date_value.strftime("Date: %d %B %Y"), "muted"))

        if not parsed.entries and not parsed.flagged_lines:
            out += [("", None), ("No patient entries were found in this PDF.", "warn")]
            self._write(out)
            return

        wrote, tab_name, error, is_new = 0, None, None, False
        if parsed.entries:
            try:
                wb, ws, is_new, stamp = excel_writer.load_or_create_workbook(
                    self.records_folder, parsed.date_value)
                excel_writer.append_entries(ws, parsed.date_value, parsed.entries)
                tab_name = ws.title
                excel_writer.save_with_backup(
                    wb, excel_writer.workbook_path(self.records_folder),
                    config.get_backups_dir(), expected_stamp=stamp)
                wrote = len(parsed.entries)
                if getattr(self, "_fingerprint", None):
                    history.remember(self.records_folder, self._fingerprint,
                                     pdf_path, tab_name, wrote)
            except excel_writer.ExcelWriteError as e:
                error = str(e)
            except excel_writer.ConcurrentChangeError as e:
                error = str(e)
            except PermissionError:
                error = (f"'{excel_writer.WORKBOOK_NAME}' is currently open in Excel, "
                         f"so it could not be added to.\n\n"
                         f"Please close it in Excel, then try again.\n\n"
                         f"Nothing has been lost — just close it and try once more.")
            except Exception as e:
                error = f"Unexpected error while saving: {e}"

        if error:
            out += [("", None), ("Nothing was saved.", "err"), ("", None)]
            out += [(line, "muted") for line in error.split("\n")]
            self._set_tiles(0, len(parsed.flagged_lines))
            self._write(out)
            return

        self._set_tiles(wrote, len(parsed.flagged_lines), tab_name or "—")

        out += [
            ("", None),
            (f"Added {wrote} row{'s' if wrote != 1 else ''} to the "
             f"'{tab_name}' tab{' (new tab created)' if is_new else ''}.", "ok"),
            (excel_writer.workbook_path(self.records_folder), "muted"),
        ]

        if parsed.entries:
            out += [("", None), ("Entries added", "head")]
            for e in parsed.entries:
                bits = [e["PATIENT NAME"]]
                for label, key in (("Dr ", "DOCTOR"), ("", "CODE"), ("", "NO. OF UNITS"),
                                   ("Rs ", "AMOUNT"), ("", "MOBILE NO."),
                                   ("", "MISCELLANEOUS")):
                    if e[key]:
                        bits.append(f"{label}{e[key]}")
                out.append(("  •  " + "  ·  ".join(bits), None))

        if parsed.flagged_lines:
            out += [
                ("", None),
                (f"{len(parsed.flagged_lines)} line(s) need checking by hand", "warn"),
                ("These were NOT added, because they couldn't be understood for certain:",
                 "muted"),
            ]
            for line_text, reason in parsed.flagged_lines:
                out.append((f"  •  {line_text}", None))
                out.append((f"     {reason}", "muted"))

        self._write(out)


def main():
    root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
