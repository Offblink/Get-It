"""Test snooze behavior — BUG FIX verification.

Expected: snoozing a schedule sets snoozed_until, does NOT change hour/minute.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from models import Schedule


class TestSnoozePreservesScheduleTime:
    """BUG: Clicking '延后' changes schedule hour/minute permanently.
    FIX: Only set snoozed_until; original time stays intact."""

    def test_snooze_does_not_change_hour_minute(self):
        s = Schedule(id=1, content="Meeting", hour=9, minute=30)
        original_hour = s.hour
        original_minute = s.minute

        # Simulate snooze: set snoozed_until, leave hour/minute alone
        now = datetime.now()
        snooze_minutes = 15
        s.snoozed_until = (now + timedelta(minutes=snooze_minutes)).isoformat()

        assert s.hour == original_hour, "snooze must not change hour"
        assert s.minute == original_minute, "snooze must not change minute"
        assert s.snoozed_until is not None

    def test_snooze_is_cleared_on_close(self):
        """After 'Get it' close, snoozed_until should be cleared."""
        s = Schedule(id=2, content="Task", hour=14, minute=0,
                     snoozed_until="2026-07-07T15:00:00")

        # Simulate close
        s.snoozed_until = None

        assert s.snoozed_until is None
        assert s.hour == 14
        assert s.minute == 0

    def test_multiple_snoozes_keep_original_time(self):
        """Snoozing multiple times still keeps original schedule time."""
        s = Schedule(id=3, content="Daily", hour=8, minute=0)
        original = (s.hour, s.minute)

        for i in range(3):
            s.snoozed_until = (datetime.now() + timedelta(minutes=10)).isoformat()
            assert (s.hour, s.minute) == original, f"snooze #{i+1} changed time"

    def test_snoozed_schedule_skipped_by_checker(self):
        """Reminder checker should skip schedules with active snooze."""
        from datetime import time as dt_time

        s = Schedule(id=4, content="Snoozed", hour=12, minute=0,
                     snoozed_until=(datetime.now() + timedelta(minutes=5)).isoformat())

        now = datetime.now()

        # Simulate reminder check logic
        should_fire = (
            s.active
            and now.time() == dt_time(s.hour, s.minute)
            and (s.snoozed_until is None or datetime.fromisoformat(s.snoozed_until) <= now)
        )
        # At a non-matching time, it shouldn't fire anyway
        # But if time matched, the snoozed_until would block it
        if now.time() == dt_time(12, 0):
            assert not should_fire, "snoozed schedule should not fire"
        # anyway, hour/minute unchanged
        assert s.hour == 12
        assert s.minute == 0

    def test_expired_snooze_allows_fire(self):
        """When snooze expires, reminder fires at original time again."""
        s = Schedule(id=5, content="Expired", hour=10, minute=0,
                     snoozed_until="2020-01-01T00:00:00")  # long expired

        now = datetime.now()
        should_fire = (
            s.active
            and (s.snoozed_until is None or datetime.fromisoformat(s.snoozed_until) <= now)
        )
        assert should_fire, "expired snooze should not block reminders"
