"""
Reads the text out of a dictated daily PDF and turns it into structured
patient entries, ready to be written into Excel.

Real-world format (confirmed from an actual Wispr Flow dictation on
2026-08-24): one field per line, "Label: value", with a blank line between
patients, and the date once at the very top:

    Date: 1st July 2026
    Name: Akshita
    Doctor: Ranjeet Bhardwaj
    Model Number: SC1
    Number of Unit: 1 pair
    Mobile Number: 9205087776
    Amount: None
    Location: Chandigarh

    Name: Ruhani
    Doctor: Ajay Gupta
    ...

Any line that isn't attached to a recognised label (doctor, model number,
size, number of units, mobile number, amount, name) is kept as-is and
placed into the MISCELLANEOUS column. Nothing is ever guessed silently.
"""

import re
from dateutil import parser as dateparser

FIELD_ORDER = [
    "PATIENT NAME", "DOCTOR", "CODE",
    "NO. OF UNITS", "MOBILE NO.", "AMOUNT",
]

# Order doesn't matter for correctness - each pattern anchors on a distinct
# starting keyword so there's no overlap between labels.
LABEL_PATTERNS = {
    "DATE": r'^date\b[:\-]?\s*',
    "PATIENT NAME": r'^(patient\s*name|patient|name)\b[:\-]?\s*',
    "DOCTOR": r'^doctor\b[:\-]?\s*',
    "CODE": r'^(model\s*number|model\s*no\.?|model|code)\b[:\-]?\s*',
    "NO. OF UNITS": r'^(number\s*of\s*units?|no\.?\s*of\s*units?|units?|unit)\b[:\-]?\s*',
    "MOBILE NO.": r'^(mobile\s*number|mobile\s*no\.?|mobile|phone\s*number|phone\s*no\.?|phone)\b[:\-]?\s*',
    "AMOUNT": r'^(amount|rs\.?)\b[:\-]?\s*',
}

# Values that really mean "nothing was said here", not literal text.
BLANK_VALUES = {"none", "n/a", "na", "nil", "-", "null", ""}


def _normalize_code(value):
    """Model numbers like 'SC1' or 'SC66' should read 'SC-1' / 'SC-66'."""
    m = re.match(r'^([A-Za-z]+)(\d.*)$', value.strip())
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return value


def _strip_misc_label(line):
    """Turns 'Location: Chandigarh' into just 'Chandigarh' - drop any label, keep the value."""
    m = re.match(r'^[A-Za-z][A-Za-z\s]{0,24}:\s*(.+)$', line.strip())
    if m:
        return m.group(1).strip()
    return line.strip()


def _strip_leading_punctuation(text):
    """':2' and ': 2' and '- 2' all mean just '2'."""
    return re.sub(r'^[\s:\-\u2013\u2014]+', '', text).strip()


class ParsedDay:
    def __init__(self, date_value, date_raw_text, entries, flagged_lines):
        self.date_value = date_value          # a real date, or None
        self.date_raw_text = date_raw_text     # what was actually said/typed
        self.entries = entries                 # list of dicts, one per patient
        self.flagged_lines = flagged_lines      # list of (text, reason)


def _match_label(line):
    """Return (label, value) if the line starts with a known label, else (None, line)."""
    stripped = line.strip()
    for label, pattern in LABEL_PATTERNS.items():
        m = re.match(pattern, stripped, re.IGNORECASE)
        if m:
            # People write "units: 2", "units :2" and "units : 2" interchangeably,
            # so drop any leftover punctuation sitting between label and value.
            value = _strip_leading_punctuation(stripped[m.end():])
            if value.lower() in BLANK_VALUES:
                value = ""
            return label, value
    return None, stripped


def parse_date_text(raw_text):
    """Try to turn spoken/typed date text into a real date. Returns None if unsure."""
    if not raw_text:
        return None
    try:
        return dateparser.parse(raw_text, fuzzy=True, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def _split_into_blocks(lines):
    """
    Group lines into blocks, one per patient.

    Normally a blank line separates patients. But some PDF exporters drop
    blank lines entirely, which would otherwise merge everybody into a single
    patient and silently lose the rest - so a fresh 'Name:' line also starts a
    new patient, whether or not there was a gap before it.
    """
    blocks = []
    current = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
            continue

        label, _ = _match_label(line)
        if label == "PATIENT NAME" and any(
                _match_label(l)[0] == "PATIENT NAME" for l in current):
            blocks.append(current)
            current = []

        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def parse_patient_block(lines):
    """Turn one patient's lines into a column-value dict, plus a Miscellaneous string."""
    entry = {k: "" for k in FIELD_ORDER}
    misc_parts = []

    for line in lines:
        label, value = _match_label(line)
        if label == "DATE":
            continue  # a stray date line inside a block isn't a patient field
        if label == "MOBILE NO." and value and not any(ch.isdigit() for ch in value):
            # e.g. "not known", "not there" - no digits at all, so leave it blank.
            value = ""
        if label and value:
            if label == "CODE":
                value = _normalize_code(value)
            if entry.get(label):
                misc_parts.append(f"(extra {label.lower()}: {value})")
            else:
                entry[label] = value
        elif label and not value:
            # Label present but nothing after it (or it was a "None"/blank marker) - skip silently.
            continue
        else:
            misc_parts.append(_strip_misc_label(line))

    entry["MISCELLANEOUS"] = "; ".join(misc_parts)
    return entry


def parse_pdf_text(text):
    """
    Parse the full text of one day's PDF.
    Blocks that don't look like a usable patient entry (e.g. no patient name
    found) are NOT guessed - they go into flagged_lines for the user to fix.
    """
    raw_lines = text.splitlines()

    date_value = None
    date_raw_text = None
    date_found = False
    remaining_lines = []

    for line in raw_lines:
        if not date_found:
            label, value = _match_label(line)
            if label == "DATE":
                date_raw_text = value
                date_value = parse_date_text(value)
                date_found = True
                continue
        remaining_lines.append(line)

    blocks = _split_into_blocks(remaining_lines)

    entries = []
    flagged_lines = []
    for block in blocks:
        entry = parse_patient_block(block)
        if not entry["PATIENT NAME"]:
            flagged_lines.append((" | ".join(l.strip() for l in block), "Could not find a patient name in this block"))
            continue
        entries.append(entry)

    if date_found and date_value is None:
        flagged_lines.append((f"Date: {date_raw_text}", "Found a date label but could not understand the date text"))

    if not date_found:
        flagged_lines.append(("(no date line found)", "No line starting with 'Date' was found in the PDF"))

    return ParsedDay(date_value, date_raw_text, entries, flagged_lines)
