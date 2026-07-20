import json
import os
import sys
from typing import Optional

from models import AppSettings


def _data_path() -> str:
    """Return absolute path to data file, next to the main script."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "daily_reminder_data.json")


class DataManager:
    def __init__(self, filepath: str = None) -> None:
        self.filepath = filepath or _data_path()

    def load(self) -> AppSettings:
        if not os.path.exists(self.filepath):
            return AppSettings()
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppSettings.from_dict(data)
        except (json.JSONDecodeError, ValueError, KeyError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
