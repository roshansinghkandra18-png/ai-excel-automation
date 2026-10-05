"""
Remembers which PDFs have already been filed, so the same day's PDF can't be
added twice by accident and quietly double up everybody's entries.

A PDF is identified by its contents, not its name - so renaming a file won't
sneak it past, and re-exporting a genuinely corrected PDF is correctly seen
as a new, different file.

The record lives beside the Excel file rather than beside the program, so if
two office PCs share the same folder they also share the same memory of what
has been filed.
"""

import hashlib
import json
import os
from datetime import datetime

HISTORY_NAME = "_filed_pdfs.json"


def history_path(records_folder):
    return os.path.join(records_folder, HISTORY_NAME)


def fingerprint(pdf_path):
    """A short signature of the file's actual contents."""
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:32]


def _load(records_folder):
    try:
        with open(history_path(records_folder), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def previous_entry(records_folder, fp):
    """Returns what we know about this PDF if it has been filed before, else None."""
    return _load(records_folder).get(fp)


def remember(records_folder, fp, pdf_path, tab, rows):
    """Records that this PDF has now been filed. Never blocks a save if it fails."""
    try:
        data = _load(records_folder)
        data[fp] = {
            "file": os.path.basename(pdf_path),
            "filed_on": datetime.now().strftime("%d %b %Y at %H:%M"),
            "tab": tab,
            "rows": rows,
        }
        with open(history_path(records_folder), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass  # a missing memory is a nuisance; a failed save would be worse
