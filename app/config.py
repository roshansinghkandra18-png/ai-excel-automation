"""Remembers which folder to save the monthly Excel files into."""

import json
import os
import sys


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(_app_dir(), "settings.json")


def load():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_records_folder():
    return load().get("records_folder")


def set_records_folder(path):
    data = load()
    data["records_folder"] = path
    save(data)


def get_backups_dir():
    """
    Defaults to a folder next to the program itself (not next to the monthly
    Excel files) so a problem with the records folder can never also wipe
    out the backup.
    """
    data = load()
    return data.get("backups_dir") or os.path.join(_app_dir(), "Excel Backups")
