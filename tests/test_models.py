"""Tests for data models."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Schedule, AppSettings


class TestSchedule:
    def test_defaults(self):
        s = Schedule(id=1, content="Test", hour=9, minute=30)
        assert s.ringtone_name == "风铃声"
        assert s.ringtone_type == "builtin"
        assert s.active is True
        assert s.snoozed_until is None

    def test_to_dict(self):
        s = Schedule(id=1, content="Hello", hour=14, minute=0,
                     content_color="#ff0000", content_font_size=14)
        d = s.to_dict()
        assert d["id"] == 1
        assert d["content"] == "Hello"
        assert d["content_color"] == "#ff0000"
        assert d["snoozed_until"] is None

    def test_from_dict_backward_compat(self):
        """Old data without snoozed_until or content_color should load."""
        old = {"id": 5, "content": "Old", "hour": 10, "minute": 30}
        s = Schedule.from_dict(old)
        assert s.id == 5
        assert s.content == "Old"
        assert s.content_color == "#000000"
        assert s.snoozed_until is None
        assert s.active is True

    def test_round_trip(self):
        s = Schedule(id=3, content="RT", hour=8, minute=15,
                     ringtone_name="警报声", ringtone_type="builtin",
                     content_color="#00ff00", content_font_size=12,
                     snoozed_until="2026-07-07T10:00:00")
        d = s.to_dict()
        s2 = Schedule.from_dict(d)
        assert s2.id == s.id
        assert s2.content == s.content
        assert s2.hour == s.hour
        assert s2.minute == s.minute
        assert s2.snoozed_until == "2026-07-07T10:00:00"


class TestAppSettings:
    def test_defaults(self):
        s = AppSettings()
        assert s.character_name == "雨子酱"
        assert s.default_snooze_minutes == 10
        assert s.close_behavior == "minimize_to_tray"
        assert s.schedules == []

    def test_to_dict_with_schedules(self):
        sch = Schedule(id=1, content="X", hour=12, minute=0)
        s = AppSettings(schedules=[sch])
        d = s.to_dict()
        assert len(d["schedules"]) == 1
        assert d["schedules"][0]["content"] == "X"

    def test_from_dict_backward_compat(self):
        """Load old-format JSON (no custom_name_color etc.)."""
        old = {"schedules": [], "character_name": "Test"}
        s = AppSettings.from_dict(old)
        assert s.character_name == "Test"
        assert s.custom_name_color == "#000000"
