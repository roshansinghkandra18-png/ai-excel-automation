"""
Writes parsed patient entries into ONE Excel file that carries a tab per
calendar month (JAN 2026, FEB 2026, ...), the same way the office's older
master file works - everything in one place.

Always appends new rows below existing ones; never edits or overwrites
anything already there. Never touches the old 10-year master file.
"""

import os
import re
import shutil
import zipfile
import tempfile
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

WORKBOOK_NAME = "DAILY PATIENT RECORD.xlsx"

HEADERS = [
    "DATE", "PATIENT NAME", "DOCTOR", "CODE",
    "NO. OF UNITS", "MISCELLANEOUS", "MOBILE NO.", "AMOUNT",
]

MONTH_NAMES = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]

# 1-indexed, matching HEADERS order.
CENTER_COLUMNS = {1, 4, 5, 7, 8}   # DATE, CODE, NO. OF UNITS, MOBILE NO., AMOUNT
MOBILE_COLUMN_LETTER = "G"

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")
THIN_BORDER = Border(
    left=Side(style="thin", color="B7B7B7"),
    right=Side(style="thin", color="B7B7B7"),
    top=Side(style="thin", color="B7B7B7"),
    bottom=Side(style="thin", color="B7B7B7"),
)


class ExcelWriteError(Exception):
    """Raised when we refuse to write, to avoid mixing up existing data."""


class ConcurrentChangeError(Exception):
    """
    Raised when the record file changed on disk between us opening it and
    saving it - meaning someone else added entries in the meantime. Saving
    on top would silently erase their work, so we refuse instead.
    """


def file_stamp(path):
    """A cheap 'has this file changed?' signature. None means it didn't exist."""
    try:
        s = os.stat(path)
        return (s.st_mtime_ns, s.st_size)
    except OSError:
        return None


def sheet_name_for(d):
    return f"{MONTH_NAMES[d.month - 1]} {d.year}"


def workbook_path(records_folder):
    return os.path.join(records_folder, WORKBOOK_NAME)


def _normalize(name):
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


def _find_sheet(wb, target_name):
    target = _normalize(target_name)
    for name in wb.sheetnames:
        if _normalize(name) == target:
            return name
    return None


def _month_sort_key(sheet_name):
    """Sorts tabs chronologically, so a back-dated month lands in the right place."""
    parts = (sheet_name or "").upper().split()
    if len(parts) == 2 and parts[0] in MONTH_NAMES and parts[1].isdigit():
        return (int(parts[1]), MONTH_NAMES.index(parts[0]))
    return (9999, 99)  # anything unrecognised stays at the end


def load_or_create_workbook(records_folder, d):
    """
    Opens (or creates) the single record workbook and returns
    (workbook, worksheet_for_this_month, is_new_month_tab, stamp).

    `stamp` is what the file looked like when we opened it; hand it back to
    save_with_backup so we can tell if somebody else wrote to it meanwhile.
    Does NOT save anything yet.
    """
    path = workbook_path(records_folder)
    tab = sheet_name_for(d)
    stamp = file_stamp(path)

    if os.path.exists(path):
        wb = openpyxl.load_workbook(path)
        existing = _find_sheet(wb, tab)
        if existing:
            ws = wb[existing]
            found = [c.value for c in ws[1][: len(HEADERS)]]
            if [(h or "").strip().upper() for h in found] != [h.upper() for h in HEADERS]:
                raise ExcelWriteError(
                    f"The '{existing}' tab already exists in {WORKBOOK_NAME}, but its columns "
                    f"don't match what this program expects, so nothing was written "
                    f"(to avoid mixing up your data).\n\n"
                    f"Expected: {', '.join(HEADERS)}\n"
                    f"Found: {', '.join(str(h) for h in found)}"
                )
            return wb, ws, False, stamp
        ws = wb.create_sheet(title=tab)
        ws.append(HEADERS)
        _order_tabs(wb)
        return wb, ws, True, stamp

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = tab
    ws.append(HEADERS)
    return wb, ws, True, stamp


def _order_tabs(wb):
    """Keeps the month tabs in date order along the bottom of Excel."""
    try:
        ordered = sorted(wb.sheetnames, key=_month_sort_key)
        wb._sheets = [wb[name] for name in ordered]
    except Exception:
        pass  # tab order is a nicety, never worth failing a save over


def _best_effort_number(value):
    """Turns '10,000' or '5000' into a real number. Leaves genuinely non-numeric text alone."""
    value = (value or "").strip()
    if not value:
        return value
    cleaned = value.replace(",", "")
    try:
        return int(cleaned)
    except ValueError:
        pass
    try:
        return float(cleaned)
    except ValueError:
        return value


def append_entries(ws, date_value, entries):
    for entry in entries:
        ws.append([
            date_value,
            entry.get("PATIENT NAME", ""),
            entry.get("DOCTOR", ""),
            entry.get("CODE", ""),
            _best_effort_number(entry.get("NO. OF UNITS", "")),
            entry.get("MISCELLANEOUS", ""),
            entry.get("MOBILE NO.", ""),
            _best_effort_number(entry.get("AMOUNT", "")),
        ])
        r = ws.max_row
        if date_value is not None:
            ws.cell(row=r, column=1).number_format = "DD-MMM-YYYY"
        ws.cell(row=r, column=8).number_format = "#,##0"


def style_worksheet(ws):
    """Consistent column widths, alignment, borders and a coloured header row."""
    max_row = ws.max_row
    max_col = len(HEADERS)

    for col in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    for row in range(2, max_row + 1):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(
                horizontal="center" if col in CENTER_COLUMNS else "left",
                vertical="center",
            )

    for col in range(1, max_col + 1):
        longest = len(HEADERS[col - 1])
        for row in range(2, max_row + 1):
            value = ws.cell(row=row, column=col).value
            if value is not None:
                longest = max(longest, len(str(value)))
        letter = ws.cell(row=1, column=col).column_letter
        ws.column_dimensions[letter].width = max(12, longest + 4)

    ws.freeze_panes = "A2"


def _hide_number_stored_as_text_marks(xlsx_path, sheet_rows):
    """
    Mobile numbers are deliberately kept as text (so spaces and leading zeros
    survive), but Excel then shows a green warning triangle on each one.
    openpyxl can't switch that off, so we add the 'ignore this' instruction
    into the saved file ourselves. Purely cosmetic - if anything goes wrong
    we leave the file exactly as it was.

    `sheet_rows` maps the sheet's XML file name -> its last row number.
    """
    try:
        with zipfile.ZipFile(xlsx_path, "r") as zin:
            names = zin.namelist()
            contents = {n: zin.read(n) for n in names}

        changed = False
        for target, last_row in sheet_rows.items():
            if target not in contents:
                continue
            marker = (f'<ignoredErrors><ignoredError '
                      f'sqref="{MOBILE_COLUMN_LETTER}2:{MOBILE_COLUMN_LETTER}{max(last_row, 2)}" '
                      f'numberStoredAsText="1"/></ignoredErrors>')
            xml = contents[target].decode("utf-8")
            if "<ignoredErrors" in xml:
                xml = re.sub(r"<ignoredErrors>.*?</ignoredErrors>", marker, xml, flags=re.DOTALL)
            else:
                xml = xml.replace("</worksheet>", marker + "</worksheet>")
            contents[target] = xml.encode("utf-8")
            changed = True

        if not changed:
            return

        fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                zout.writestr(n, contents[n])
        shutil.move(tmp_path, xlsx_path)
    except Exception:
        return


def save_with_backup(wb, live_path, backups_dir, expected_stamp="skip"):
    """
    Styles every month tab, saves the workbook, then mirrors it into the
    backups folder.

    If `expected_stamp` is given, the file is checked immediately before
    writing: if it no longer matches, somebody else has saved to it since we
    opened it, and we refuse rather than wipe out their entries.
    """
    if expected_stamp != "skip" and file_stamp(live_path) != expected_stamp:
        raise ConcurrentChangeError(
            "Somebody else added entries to the record while this PDF was being read.\n\n"
            "Nothing was saved, so none of their work has been lost.\n\n"
            "Please try adding this PDF again - it will pick up their entries first."
        )

    for ws in wb.worksheets:
        try:
            style_worksheet(ws)
        except Exception:
            pass

    sheet_rows = {
        f"xl/worksheets/sheet{i + 1}.xml": ws.max_row
        for i, ws in enumerate(wb.worksheets)
    }

    os.makedirs(os.path.dirname(live_path) or ".", exist_ok=True)
    wb.save(live_path)
    _hide_number_stored_as_text_marks(live_path, sheet_rows)

    os.makedirs(backups_dir, exist_ok=True)
    backup_path = os.path.join(backups_dir, os.path.basename(live_path))
    shutil.copy2(live_path, backup_path)
    return backup_path
