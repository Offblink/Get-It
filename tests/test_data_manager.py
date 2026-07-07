"""Tests for DataManager JSON persistence."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import DataManager
from models import AppSettings, Schedule


class TestDataManager:
    def test_load_missing_file_returns_defaults(self):
        dm = DataManager("nonexistent_test.json")
        s = dm.load()
        assert s.character_name == "雨子酱"
        assert s.schedules == []

    def test_save_and_load_roundtrip(self):
        sch = Schedule(id=1, content="Test", hour=9, minute=30,
                       content_color="#ff0000", content_font_size=14)
        settings = AppSettings(schedules=[sch], character_name="TestChar")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
            tmp = f.name

        try:
            dm = DataManager(tmp)
            dm.save(settings)
            loaded = dm.load()
            assert loaded.character_name == "TestChar"
            assert len(loaded.schedules) == 1
            assert loaded.schedules[0].content == "Test"
            assert loaded.schedules[0].content_color == "#ff0000"
            assert loaded.schedules[0].content_font_size == 14
        finally:
            os.unlink(tmp)

    def test_save_writes_valid_json(self):
        settings = AppSettings()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            dm = DataManager(tmp)
            dm.save(settings)
            with open(tmp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert "schedules" in data
            assert "character_name" in data
        finally:
            os.unlink(tmp)
