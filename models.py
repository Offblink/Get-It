from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Schedule:
    id: int
    content: str
    hour: int
    minute: int
    ringtone_name: str = "风铃声"
    ringtone_key: str = "风铃声"
    ringtone_type: str = "builtin"  # "builtin" | "custom"
    custom_ringtone_path: Optional[str] = None
    content_color: str = "#000000"
    content_font_size: int = 10
    active: bool = True
    last_triggered: Optional[str] = None  # ISO datetime
    snoozed_until: Optional[str] = None   # ISO datetime — NEW: tracks snooze expiry without changing schedule time

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert None to null for JSON compat
        return d

    @classmethod
    def from_dict(cls, d: dict, next_id: int = None) -> 'Schedule':
        # Fill in defaults for backward compat with old data
        defaults = {
            'ringtone_name': '风铃声', 'ringtone_key': '风铃声',
            'ringtone_type': 'builtin', 'custom_ringtone_path': None,
            'content_color': '#000000', 'content_font_size': 10,
            'active': True, 'last_triggered': None, 'snoozed_until': None
        }
        for k, v in defaults.items():
            d.setdefault(k, v)
        if next_id is not None:
            d['id'] = next_id
        # Clamp out-of-range values to prevent crashes
        d['hour'] = max(0, min(23, int(d.get('hour', 0))))
        d['minute'] = max(0, min(59, int(d.get('minute', 0))))
        return cls(**{k: d[k] for k in [
            'id', 'content', 'hour', 'minute', 'ringtone_name', 'ringtone_key',
            'ringtone_type', 'custom_ringtone_path', 'content_color',
            'content_font_size', 'active', 'last_triggered', 'snoozed_until'
        ]})


@dataclass
class AppSettings:
    schedules: list = field(default_factory=list)
    default_snooze_minutes: int = 10
    character_name: str = "雨子酱"
    character_name_color: str = "#000000"
    character_name_font_size: int = 12
    character_avatar_path: Optional[str] = None
    schedule_content_color: str = "#000000"
    schedule_content_font_size: int = 10
    close_behavior: str = "minimize_to_tray"
    catch_up_missed: bool = True  # NEW: fire missed reminders on wake/resume
    custom_schedule_color: str = "#000000"
    custom_name_color: str = "#000000"

    def to_dict(self) -> dict:
        return {
            'schedules': [s.to_dict() for s in self.schedules],
            'default_snooze_minutes': self.default_snooze_minutes,
            'character_name': self.character_name,
            'character_name_color': self.character_name_color,
            'character_name_font_size': self.character_name_font_size,
            'character_avatar_path': self.character_avatar_path,
            'schedule_content_color': self.schedule_content_color,
            'schedule_content_font_size': self.schedule_content_font_size,
            'close_behavior': self.close_behavior,
            'catch_up_missed': self.catch_up_missed,
            'custom_schedule_color': self.custom_schedule_color,
            'custom_name_color': self.custom_name_color,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'AppSettings':
        schedules = [Schedule.from_dict(s) for s in d.get('schedules', [])]
        return cls(
            schedules=schedules,
            default_snooze_minutes=d.get('default_snooze_minutes', 10),
            character_name=d.get('character_name', '雨子酱'),
            character_name_color=d.get('character_name_color', '#000000'),
            character_name_font_size=d.get('character_name_font_size', 12),
            character_avatar_path=d.get('character_avatar_path'),
            schedule_content_color=d.get('schedule_content_color', '#000000'),
            close_behavior=d.get('close_behavior', 'minimize_to_tray'),
            catch_up_missed=d.get('catch_up_missed', True),
            custom_schedule_color=d.get('custom_schedule_color', '#000000'),
            custom_name_color=d.get('custom_name_color', '#000000'),
        )
