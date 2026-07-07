"""Get It — Daily Reminder Application (PyQt6).

Single-file version. Run: python Get_It.pyw [--minimized]
"""

# ── Imports ────────────────────────────────────────────────────────────────
import json, math, os, sys, time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
import pygame
from PIL import Image, ImageDraw, ImageQt

from PyQt6.QtCore import (
    Qt, QPoint, QPointF, QRectF, QTimer,
    QPropertyAnimation, QEasingCurve, pyqtSignal, QThread,
    QSharedMemory,
)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtGui import (
    QAction, QColor, QFont, QIcon, QImage,
    QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QColorDialog,
    QComboBox, QDialog, QFileDialog, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMenu,
    QMessageBox, QPushButton, QRadioButton, QSizePolicy,
    QSpinBox, QStyle, QSystemTrayIcon, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

# ── Constants ──────────────────────────────────────────────────────────────
COLOR_NAMES = {
    "黑色": "#000000", "深灰色": "#333333", "蓝色": "#0000FF",
    "绿色": "#008000", "红色": "#FF0000", "棕色": "#8B4513",
    "紫色": "#800080", "橙色": "#FFA500", "自定义颜色": "custom",
}
COLOR_TO_NAME = {v: k for k, v in COLOR_NAMES.items() if k != "自定义颜色"}
BUILTIN_RINGTONES = ["叮咚声", "风铃声", "蜂鸣声", "警报声", "通知音", "钢琴音", "合成器"]
NAME_FONT_SIZES = ["12", "14", "16", "18", "20", "24"]
CONTENT_FONT_SIZES = ["10", "12", "14", "16", "18", "20"]

def get_color_name(hex_color: str) -> str:
    if hex_color in COLOR_TO_NAME:
        return COLOR_TO_NAME[hex_color]
    for name, code in COLOR_NAMES.items():
        if code == hex_color:
            return name
    return "自定义颜色"

# ── Path helpers (exe-aware) ───────────────────────────────────────────────
def _app_dir() -> str:
    """Directory containing the exe or script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _data_path() -> str:
    return os.path.join(_app_dir(), "daily_reminder_data.json")

def _icon_path() -> str:
    return os.path.join(_app_dir(), "icon.ico")

# ═══ ringtone ═══
import numpy as np
import pygame


class RingtoneGenerator:
    """Modern ringtone generator with 7 distinct sounds."""

    @staticmethod
    def _make_stereo(mono_array: np.ndarray) -> np.ndarray:
        """Convert mono array to stereo."""
        if len(mono_array.shape) == 1:
            return np.column_stack((mono_array, mono_array))
        return mono_array

    @staticmethod
    def create_dingdong() -> pygame.mixer.Sound:
        """Generate an elegant ding-dong chime."""
        duration: float = 1.2
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Harmonious note combination
        freq1: float = 880  # A5
        freq2: float = 660  # E5
        sound1: np.ndarray = 0.6 * np.sin(2 * np.pi * freq1 * t[: int(0.4 * sample_rate)])
        sound2: np.ndarray = 0.6 * np.sin(2 * np.pi * freq2 * t[: int(0.4 * sample_rate)])

        # Add harmonics
        sound1 += 0.2 * np.sin(2 * np.pi * freq1 * 2 * t[: int(0.4 * sample_rate)])
        sound2 += 0.2 * np.sin(2 * np.pi * freq2 * 2 * t[: int(0.4 * sample_rate)])

        audio: np.ndarray = np.zeros(samples)
        audio[0 : len(sound1)] = sound1
        audio[int(0.5 * sample_rate) : int(0.5 * sample_rate) + len(sound2)] = sound2

        # Smoother envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.1 * sample_rate)
        decay: int = int(0.3 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack : attack + decay] = np.exp(-3 * (t[attack : attack + decay] - 0.1))
        envelope[attack + decay :] = np.exp(-8 * (t[attack + decay :] - 0.4))

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_chime() -> pygame.mixer.Sound:
        """Generate a pleasant wind chime sound."""
        duration: float = 2.5
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Wind chime note sequence
        frequencies: list[float] = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
        amplitudes: list[float] = [0.5, 0.4, 0.3, 0.2]
        audio: np.ndarray = np.zeros(samples)

        for i, (freq, amp) in enumerate(zip(frequencies, amplitudes)):
            start: float = i * 0.3
            if start < duration:
                freq_duration: float = duration - start
                freq_samples: int = int(freq_duration * sample_rate)
                freq_t: np.ndarray = np.linspace(0, freq_duration, freq_samples, False)

                # Bell-like characteristics
                freq_audio: np.ndarray = amp * (
                    np.sin(2 * np.pi * freq * freq_t)
                    + 0.3 * np.sin(2 * np.pi * freq * 2 * freq_t)
                    + 0.1 * np.sin(2 * np.pi * freq * 3 * freq_t)
                )

                # Exponential decay envelope
                freq_envelope: np.ndarray = np.exp(-1.5 * freq_t)
                freq_audio = freq_audio * freq_envelope

                start_sample: int = int(start * sample_rate)
                end_sample: int = start_sample + len(freq_audio)
                if end_sample <= samples:
                    audio[start_sample:end_sample] += freq_audio

        audio = (audio * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_beep() -> pygame.mixer.Sound:
        """Generate a modern beep sound."""
        duration: float = 0.6
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Frequency modulation for modern feel
        base_freq: float = 1200
        mod_freq: float = 8
        mod_depth: float = 100
        freq: np.ndarray = base_freq + mod_depth * np.sin(2 * np.pi * mod_freq * t)

        # Square wave mixed with sine wave
        square_wave: np.ndarray = 0.5 * np.sign(np.sin(2 * np.pi * freq * t))
        sine_wave: np.ndarray = 0.3 * np.sin(2 * np.pi * freq * t)
        audio: np.ndarray = 0.7 * square_wave + 0.3 * sine_wave

        # Carefully designed envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.05 * sample_rate)
        sustain: int = int(0.4 * sample_rate)
        release: int = int(0.15 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack : attack + sustain] = 0.8
        envelope[attack + sustain :] = np.linspace(0.8, 0, release)

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_alert() -> pygame.mixer.Sound:
        """Generate a professional alert sound."""
        duration: float = 1.2
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Alternating frequencies for urgency
        freq_high: float = 1600
        freq_low: float = 1000
        switch_rate: int = 6
        audio: np.ndarray = np.zeros(samples)

        for i in range(int(duration * switch_rate)):
            start_sample: int = int(i * sample_rate / switch_rate)
            end_sample: int = int((i + 0.5) * sample_rate / switch_rate)

            if i % 2 == 0:
                # High-frequency part with harmonics
                segment: np.ndarray = 0.5 * (
                    np.sin(2 * np.pi * freq_high * t[start_sample:end_sample])
                    + 0.2 * np.sin(2 * np.pi * freq_high * 2 * t[start_sample:end_sample])
                )
            else:
                segment = 0.5 * np.sin(2 * np.pi * freq_low * t[start_sample:end_sample])

            if end_sample <= samples:
                audio[start_sample:end_sample] = segment

        # Dynamic envelope
        envelope: np.ndarray = np.exp(-1.2 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 2 * t))

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_notification() -> pygame.mixer.Sound:
        """Generate a modern notification sound."""
        duration: float = 0.8
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Rising frequency for positive feel
        start_freq: float = 800
        end_freq: float = 1200
        freq: np.ndarray = np.linspace(start_freq, end_freq, samples)

        audio: np.ndarray = 0.7 * np.sin(2 * np.pi * freq * t)

        # Fast attack, slow release envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.1 * sample_rate)
        release_start: int = int(0.3 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[release_start:] = np.exp(-3 * (t[release_start:] - 0.3))

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_piano() -> pygame.mixer.Sound:
        """Generate a piano tone."""
        duration: float = 1.5
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Piano harmonics
        frequencies: list[float] = [261.63, 523.25, 784.88, 1046.50]  # C4, C5, G5, C6
        amplitudes: list[float] = [0.7, 0.5, 0.3, 0.2]

        audio: np.ndarray = np.zeros(samples)
        for freq, amp in zip(frequencies, amplitudes):
            # Each harmonic has a different decay rate
            decay_rate: float = 1.0 + 0.5 * (freq / 261.63)
            freq_envelope: np.ndarray = np.exp(-decay_rate * t)
            audio += amp * np.sin(2 * np.pi * freq * t) * freq_envelope

        # Add percussive attack
        attack_env: np.ndarray = np.exp(-15 * t)
        audio = audio * attack_env

        audio = (audio * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)

    @staticmethod
    def create_synth() -> pygame.mixer.Sound:
        """Generate a synthesizer tone."""
        duration: float = 1.0
        sample_rate: int = 44100
        samples: int = int(sample_rate * duration)
        t: np.ndarray = np.linspace(0, duration, samples, False)

        # Multiple oscillators for rich timbre
        freq1: float = 440  # A4
        freq2: float = 554.37  # C#5
        audio: np.ndarray = (
            0.5 * np.sin(2 * np.pi * freq1 * t)
            + 0.3 * np.sin(2 * np.pi * freq2 * t)
            + 0.1 * np.sin(2 * np.pi * freq1 * 2 * t)
            + 0.1 * np.sin(2 * np.pi * freq2 * 2 * t)
        )

        # Low-pass filter effect
        filter_env: np.ndarray = np.exp(-2 * t)
        audio = audio * (0.8 + 0.2 * filter_env)

        # Envelope
        envelope: np.ndarray = np.ones(samples)
        attack: int = int(0.05 * sample_rate)
        decay: int = int(0.3 * sample_rate)
        sustain: float = 0.7
        release: int = int(0.2 * sample_rate)

        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack : attack + decay] = np.linspace(1, sustain, decay)
        envelope[attack + decay : -release] = sustain
        envelope[-release:] = np.linspace(sustain, 0, release)

        audio = (audio * envelope * 32767).astype(np.int16)
        stereo_audio: np.ndarray = RingtoneGenerator._make_stereo(audio)
        return pygame.sndarray.make_sound(stereo_audio)


# ═══ models ═══
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


# ═══ data_manager ═══


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


# ═══ avatar_cropper ═══
import os
import math
import time
from io import BytesIO

from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QPixmap, QImage
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QSizePolicy
)
from PIL import Image, ImageDraw


def _pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    """Convert a PIL Image to QPixmap via a buffer."""
    if pil_image.mode == "RGBA":
        fmt = "PNG"
    else:
        pil_image = pil_image.convert("RGBA")
        fmt = "PNG"
    buf = BytesIO()
    pil_image.save(buf, format=fmt)
    buf.seek(0)
    pixmap = QPixmap()
    pixmap.loadFromData(buf.read(), fmt)
    return pixmap


def _qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    """Convert a QPixmap to PIL Image via a buffer."""
    buf = BytesIO()
    pixmap.save(buf, "PNG")
    buf.seek(0)
    return Image.open(buf)


class _CropperPreview(QWidget):
    """Inner widget that displays the image and crop overlay."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self.setFixedSize(pixmap.width(), pixmap.height())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

        # Crop area state
        self.crop_x: float = pixmap.width() / 2.0
        self.crop_y: float = pixmap.height() / 2.0
        self.crop_radius: float = min(pixmap.width(), pixmap.height()) / 3.0
        self._min_radius: float = 20.0

        # Interaction state
        self.dragging: bool = False
        self.drag_type: str | None = None  # 'move' | 'resize'

        # Colors
        self._mask_color = QColor(0, 0, 0, 150)
        self._circle_pen = QPen(QColor(220, 50, 50), 2)

    # ── properties ──────────────────────────────────────────────

    @property
    def pixmap(self) -> QPixmap:
        return self._pixmap

    @property
    def image_rect(self) -> QRectF:
        return QRectF(0, 0, self._pixmap.width(), self._pixmap.height())

    # ── painting ────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw the image
        painter.drawPixmap(0, 0, self._pixmap)

        # 2. Draw the semi-transparent mask with a circular cutout
        self._draw_mask(painter)

        # 3. Draw the crop circle outline
        painter.setPen(self._circle_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            QPointF(int(self.crop_x), int(self.crop_y)),
            int(self.crop_radius),
            int(self.crop_radius),
        )

        painter.end()

    def _draw_mask(self, painter: QPainter):
        """Draw dark overlay with transparent circle punched out."""
        full = QPainterPath()
        full.addRect(self.image_rect)

        hole = QPainterPath()
        hole.addEllipse(
            QPointF(int(self.crop_x), int(self.crop_y)),
            int(self.crop_radius),
            int(self.crop_radius),
        )

        mask_path = full.subtracted(hole)
        painter.fillPath(mask_path, self._mask_color)

    # ── interaction helpers ─────────────────────────────────────

    def _hit_test(self, pos: QPoint) -> str | None:
        """Return 'move', 'resize', or None based on click position."""
        dx = pos.x() - self.crop_x
        dy = pos.y() - self.crop_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist <= self.crop_radius:
            return "move"

        edge_dist = abs(dist - self.crop_radius)
        if edge_dist <= 12:
            return "resize"

        return None

    def _clamp_crop_position(self):
        """Keep the crop circle fully within the image bounds."""
        r = self.crop_radius
        w = self._pixmap.width()
        h = self._pixmap.height()
        self.crop_x = max(r, min(w - r, self.crop_x))
        self.crop_y = max(r, min(h - r, self.crop_y))

    def _clamp_crop_radius(self):
        """Ensure radius stays within valid range and circle stays in bounds."""
        max_r = min(
            self.crop_x,
            self.crop_y,
            self._pixmap.width() - self.crop_x,
            self._pixmap.height() - self.crop_y,
        )
        self.crop_radius = max(self._min_radius, min(max_r, self.crop_radius))

    # ── mouse events ────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._hit_test(event.pos())
            if hit is not None:
                self.dragging = True
                self.drag_type = hit
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            pos = event.pos()
            if self.drag_type == "move":
                self.crop_x = pos.x()
                self.crop_y = pos.y()
                self._clamp_crop_position()
            elif self.drag_type == "resize":
                dx = pos.x() - self.crop_x
                dy = pos.y() - self.crop_y
                self.crop_radius = math.sqrt(dx * dx + dy * dy)
                self._clamp_crop_radius()
                self._clamp_crop_position()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.drag_type = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.crop_radius += 5
        else:
            self.crop_radius -= 5
        self._clamp_crop_radius()
        self._clamp_crop_position()
        self.update()
        event.accept()


class AvatarCropper(QDialog):
    """Modal dialog for cropping a circular avatar from an image."""

    def __init__(self, parent, image_path: str):
        super().__init__(parent)
        self.setWindowTitle("头像裁剪")
        self.setModal(True)
        self.setFixedSize(620, 620)

        # Attempt to set icon
        if os.path.exists(_icon_path()):
            try:
                self.setWindowIcon(QIcon(_icon_path()))
            except Exception:
                pass

        self.image_path = image_path

        # Load and scale
        self.original_image = Image.open(image_path)
        self.image_width, self.image_height = self.original_image.size

        self.scale_factor = min(400.0 / self.image_width, 400.0 / self.image_height)
        self.display_width = int(self.image_width * self.scale_factor)
        self.display_height = int(self.image_height * self.scale_factor)

        self.display_image = self.original_image.resize(
            (self.display_width, self.display_height), Image.Resampling.LANCZOS
        )

        # Result state
        self._cropped_pixmap: QPixmap | None = None
        self._avatar_filename: str | None = None
        self._cancelled: bool = True

        self._build_ui()

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("头像裁剪")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Instructions
        instr = QLabel(
            "拖动和缩放圆形选择区域，然后点击确认裁剪\n"
            "裁剪的头像将自动缩放为100x100像素的圆形头像"
        )
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instr.setWordWrap(True)
        instr.setStyleSheet("font-size: 12px; color: #555;")
        layout.addWidget(instr)

        # Image preview area — centered
        preview_layout = QHBoxLayout()
        preview_layout.addStretch()
        pixmap = _pil_to_qpixmap(self.display_image)
        self._preview = _CropperPreview(pixmap)
        preview_layout.addWidget(self._preview)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)
        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        confirm_btn = QPushButton("确认裁剪")
        confirm_btn.setFixedWidth(120)
        confirm_btn.clicked.connect(self._confirm_crop)
        btn_layout.addWidget(confirm_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(120)
        cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    # ── crop logic ──────────────────────────────────────────────

    def _confirm_crop(self):
        """Crop the image to a circle, resize to 100x100, save, and accept."""
        preview = self._preview

        # Map display coordinates back to original image coordinates
        scale_x = self.image_width / self.display_width
        scale_y = self.image_height / self.display_height

        actual_x = int(preview.crop_x * scale_x)
        actual_y = int(preview.crop_y * scale_y)
        actual_radius = int(preview.crop_radius * min(scale_x, scale_y))

        left = max(0, actual_x - actual_radius)
        upper = max(0, actual_y - actual_radius)
        right = min(self.image_width, actual_x + actual_radius)
        lower = min(self.image_height, actual_y + actual_radius)

        # Crop the rectangular region
        cropped = self.original_image.crop((left, upper, right, lower))

        # Make square
        size = min(cropped.size)
        cropped = cropped.resize((size, size), Image.Resampling.LANCZOS)

        # Create circular mask
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)

        # Apply mask
        result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        result.putalpha(mask)
        result.paste(cropped, (0, 0), mask)

        # Resize to 100x100
        result = result.resize((100, 100), Image.Resampling.LANCZOS)

        # Save
        avatar_filename = f"avatar_{int(time.time())}.png"
        result.save(avatar_filename, "PNG")

        self._cropped_pixmap = _pil_to_qpixmap(result)
        self._avatar_filename = avatar_filename
        self._cancelled = False
        self.accept()

    def _cancel(self):
        """Cancel the dialog."""
        self._cancelled = True
        self.reject()

    # ── result accessor ─────────────────────────────────────────

    def get_result(self) -> tuple[QPixmap | None, str | None, bool]:
        """Return (cropped_pixmap, filename, cancelled)."""
        return self._cropped_pixmap, self._avatar_filename, self._cancelled


# ═══ schedule_list ═══
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import pyqtSignal, Qt



COLOR_NAMES = {
    "黑色": "#000000",
    "深灰色": "#333333",
    "蓝色": "#0000FF",
    "绿色": "#008000",
    "红色": "#FF0000",
    "棕色": "#8B4513",
    "紫色": "#800080",
    "橙色": "#FFA500",
    "自定义颜色": "custom",
}


def _get_color_name(hex_color: str) -> str:
    for name, code in COLOR_NAMES.items():
        if code == hex_color:
            return name
    return "自定义颜色"


class ScheduleListWidget(QWidget):
    """Displays schedules in a QTreeWidget with delete support."""

    schedule_selected = pyqtSignal(object)
    schedule_deleted = pyqtSignal(object)
    new_schedule_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._schedules: list[Schedule] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Title row
        title_row = QHBoxLayout()
        title = QLabel("今日日程")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_row.addWidget(title)
        title_row.addStretch()
        new_btn = QPushButton("＋ 新建日程")
        new_btn.clicked.connect(lambda: self.new_schedule_requested.emit())
        title_row.addWidget(new_btn)
        layout.addLayout(title_row)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["时间", "内容", "铃声", "颜色", "字体"])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setRootIsDecorated(False)
        self.tree.setSortingEnabled(True)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 80)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 200)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 80)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 60)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 40)

        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        # Delete button
        delete_btn = QPushButton("删除选中日程")
        delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(delete_btn)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int):
        sched = item.data(0, Qt.ItemDataRole.UserRole)
        if sched is not None:
            self.schedule_selected.emit(sched)

    def _on_delete(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择一个日程")
            return

        item = selected[0]
        sched = item.data(0, Qt.ItemDataRole.UserRole)
        if sched is None:
            return

        # Remove from parent list
        if sched in self._schedules:
            self._schedules.remove(sched)

        self.schedule_deleted.emit(sched)
        self.refresh(self._schedules)

    def refresh(self, schedules: list[Schedule]):
        self._schedules = list(schedules)
        self.tree.clear()
        # Disable sorting while populating so the sort is controlled
        self.tree.setSortingEnabled(False)

        # Sort by time ascending
        sorted_schedules = sorted(schedules, key=lambda s: (s.hour, s.minute))

        for s in sorted_schedules:
            time_str = f"{s.hour:02d}:{s.minute:02d}"
            color_name = _get_color_name(s.content_color)
            font_str = str(s.content_font_size)

            item = QTreeWidgetItem()
            item.setText(0, time_str)
            item.setText(1, s.content)
            item.setText(2, s.ringtone_name)
            item.setText(3, color_name)
            item.setText(4, font_str)

            item.setData(0, Qt.ItemDataRole.UserRole, s)
            self.tree.addTopLevelItem(item)

        self.tree.setSortingEnabled(True)

    def clear_selection(self):
        self.tree.clearSelection()

    def get_selected_schedule(self) -> Schedule | None:
        selected = self.tree.selectedItems()
        if not selected:
            return None
        return selected[0].data(0, Qt.ItemDataRole.UserRole)


# ═══ schedule_editor ═══
from PyQt6.QtWidgets import (
    QGroupBox, QLabel, QTextEdit, QComboBox, QSpinBox,
    QPushButton, QHBoxLayout, QVBoxLayout,
    QFileDialog, QColorDialog,
)
from PyQt6.QtCore import pyqtSignal


# ── Constants ──────────────────────────────────────────────────────────────

COLOR_NAMES = {
    "黑色": "#000000",
    "深灰色": "#333333",
    "蓝色": "#0000FF",
    "绿色": "#008000",
    "红色": "#FF0000",
    "棕色": "#8B4513",
    "紫色": "#800080",
    "橙色": "#FFA500",
    "自定义颜色": "custom",
}

BUILTIN_RINGTONES = [
    "叮咚声", "风铃声", "蜂鸣声", "警报声",
    "通知音", "钢琴音", "合成器",
]

FONT_SIZES = ["10", "12", "14", "16", "18", "20"]

DEFAULT_COLOR_NAME = "黑色"
DEFAULT_FONT_SIZE = "10"
DEFAULT_BUILTIN_RINGTONE = "风铃声"
DEFAULT_HOUR = 9
DEFAULT_MINUTE = 0

CUSTOM_RINGTONE_FILTER = "音频文件 (*.mp3 *.wav *.ogg);;所有文件 (*.*)"



class ZPaddedSpinBox(QSpinBox):
    """QSpinBox that displays values with leading zeros (e.g. 09 instead of 9)."""
    def textFromValue(self, value: int) -> str:
        return f"{value:02d}"

# ── Widget ─────────────────────────────────────────────────────────────────

class ScheduleEditor(QGroupBox):
    """Editor widget for adding or editing a schedule."""

    # Signals
    schedule_saved = pyqtSignal(Schedule)
    test_notification_requested = pyqtSignal(Schedule)
    preview_builtin_ringtone = pyqtSignal(str)
    preview_custom_ringtone = pyqtSignal(str)
    stop_preview = pyqtSignal()
    custom_ringtone_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("添加/编辑日程", parent)

        self._editing_schedule_id: int | None = None
        self._custom_ringtone_path: str | None = None
        self._custom_color: str = "#000000"  # custom color from QColorDialog

        self._setup_ui()
        self._connect_signals()

    # ── UI Setup ───────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build the complete form layout."""
        layout = QVBoxLayout(self)

        # ── Row 0: Schedule content ──
        self._content_label = QLabel("日程内容:")
        self._content_edit = QTextEdit()
        self._content_edit.setPlaceholderText("输入日程内容...")
        self._content_edit.setFixedHeight(72)  # ~3 lines
        layout.addWidget(self._content_label)
        layout.addWidget(self._content_edit)

        # ── Row 1: Content style (color + font size) ──
        style_layout = QHBoxLayout()

        style_layout.addWidget(QLabel("内容颜色:"))
        self._color_combo = QComboBox()
        self._color_combo.addItems(COLOR_NAMES.keys())
        self._color_combo.setCurrentText(DEFAULT_COLOR_NAME)
        style_layout.addWidget(self._color_combo)

        self._color_preview = QLabel()
        self._color_preview.setFixedSize(20, 20)
        self._color_preview.setStyleSheet(
            f"background-color: {COLOR_NAMES[DEFAULT_COLOR_NAME]}; border: 1px solid #999;"
        )
        style_layout.addWidget(self._color_preview)

        style_layout.addWidget(QLabel("字体大小:"))
        self._font_combo = QComboBox()
        self._font_combo.addItems(FONT_SIZES)
        self._font_combo.setCurrentText(DEFAULT_FONT_SIZE)
        style_layout.addWidget(self._font_combo)

        style_layout.addStretch()
        layout.addLayout(style_layout)

        # ── Row 2: Reminder time ──
        time_layout = QHBoxLayout()

        time_layout.addWidget(QLabel("提醒时间:"))
        self._hour_spin = ZPaddedSpinBox()
        self._hour_spin.setRange(0, 23)
        self._hour_spin.setValue(DEFAULT_HOUR)
        self._hour_spin.setFixedWidth(70)
        time_layout.addWidget(self._hour_spin)

        time_layout.addWidget(QLabel(":"))

        self._minute_spin = ZPaddedSpinBox()
        self._minute_spin.setRange(0, 59)
        self._minute_spin.setValue(DEFAULT_MINUTE)
        self._minute_spin.setFixedWidth(70)
        time_layout.addWidget(self._minute_spin)

        time_layout.addStretch()
        layout.addLayout(time_layout)

        # ── Row 3: Ringtone ──
        ringtone_layout = QHBoxLayout()
        ringtone_layout.addWidget(QLabel("提醒铃声:"))

        self._builtin_combo = QComboBox()
        self._builtin_combo.addItems(BUILTIN_RINGTONES)
        self._builtin_combo.setCurrentText(DEFAULT_BUILTIN_RINGTONE)
        ringtone_layout.addWidget(self._builtin_combo)

        self._builtin_preview_btn = QPushButton("试听")
        ringtone_layout.addWidget(self._builtin_preview_btn)

        ringtone_layout.addStretch()
        layout.addLayout(ringtone_layout)

        # Custom ringtone row
        custom_layout = QHBoxLayout()

        self._custom_ringtone_label = QLabel("未选择文件")
        self._custom_ringtone_label.setStyleSheet("color: #666;")
        custom_layout.addWidget(self._custom_ringtone_label)

        self._custom_select_btn = QPushButton("选择")
        custom_layout.addWidget(self._custom_select_btn)

        self._custom_preview_btn = QPushButton("试听")
        custom_layout.addWidget(self._custom_preview_btn)

        custom_layout.addStretch()
        layout.addLayout(custom_layout)

        # ── Row 4: Action buttons ──
        action_layout = QHBoxLayout()

        self._test_notify_btn = QPushButton("立即通知")
        action_layout.addWidget(self._test_notify_btn)

        action_layout.addStretch()

        self._save_btn = QPushButton("添加日程")
        action_layout.addWidget(self._save_btn)

        layout.addLayout(action_layout)

    # ── Signal connections ─────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Wire up all internal slot connections."""
        self._color_combo.currentTextChanged.connect(self._on_color_changed)
        self._font_combo.currentTextChanged.connect(self._on_font_changed)
        self._builtin_combo.currentTextChanged.connect(self._on_builtin_ringtone_changed)

        self._builtin_preview_btn.clicked.connect(self._on_builtin_preview)
        self._custom_select_btn.clicked.connect(self._on_custom_select)
        self._custom_preview_btn.clicked.connect(self._on_custom_preview)

        self._test_notify_btn.clicked.connect(self._on_test_notify)
        self._save_btn.clicked.connect(self._on_save)

    # ── Internal slots ─────────────────────────────────────────────────────

    def _on_color_changed(self, name: str) -> None:
        """Handle color combo selection change."""
        hex_color = COLOR_NAMES.get(name, "")
        if hex_color == "custom":
            color = QColorDialog.getColor()
            if color.isValid():
                self._custom_color = color.name()
                self._color_preview.setStyleSheet(
                    f"background-color: {self._custom_color}; border: 1px solid #999;"
                )
            else:
                # Revert to black if dialog cancelled
                self._color_combo.blockSignals(True)
                self._color_combo.setCurrentText("黑色")
                self._color_combo.blockSignals(False)
                self._color_preview.setStyleSheet(
                    "background-color: #000000; border: 1px solid #999;"
                )
        else:
            self._color_preview.setStyleSheet(
                f"background-color: {hex_color}; border: 1px solid #999;"
            )

    def _on_font_changed(self, text: str) -> None:
        """Store font size selection. (Combo value is read on save.)"""
        pass  # Value read live from combo on save

    def _on_builtin_ringtone_changed(self, name: str) -> None:
        """Emit preview and clear custom ringtone path."""
        self.preview_builtin_ringtone.emit(name)
        # Clear custom ringtone state
        self._custom_ringtone_path = None
        self._custom_ringtone_label.setText("未选择文件")
        self._custom_ringtone_label.setStyleSheet("color: #666;")

    def _on_builtin_preview(self) -> None:
        """Emit preview for currently selected built-in ringtone."""
        name = self._builtin_combo.currentText()
        self.preview_builtin_ringtone.emit(name)

    def _on_custom_select(self) -> None:
        """Open file dialog for custom ringtone selection."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择铃声文件", "", CUSTOM_RINGTONE_FILTER
        )
        if filepath:
            self._custom_ringtone_path = filepath
            from pathlib import Path
            filename = Path(filepath).name
            self._custom_ringtone_label.setText(filename)
            self._custom_ringtone_label.setStyleSheet("color: #000;")
            self.custom_ringtone_selected.emit(filepath)

    def _on_custom_preview(self) -> None:
        """Emit preview for custom ringtone file."""
        if self._custom_ringtone_path:
            self.preview_custom_ringtone.emit(self._custom_ringtone_path)

    def _on_test_notify(self) -> None:
        """Build a Schedule from form data and emit test_notification_requested."""
        schedule = self._build_schedule()
        self.test_notification_requested.emit(schedule)

    def _on_save(self) -> None:
        """Build a Schedule from form data and emit schedule_saved."""
        schedule = self._build_schedule()
        self.schedule_saved.emit(schedule)

    # ── Schedule construction ──────────────────────────────────────────────

    def _build_schedule(self) -> Schedule:
        """Construct a Schedule dataclass from current form state."""
        content_color = self._resolve_content_color()

        # Determine ringtone type and path
        if self._custom_ringtone_path:
            ringtone_type = "custom"
            ringtone_name = ""  # No built-in name for custom
            ringtone_key = ""
            custom_path = self._custom_ringtone_path
        else:
            ringtone_type = "builtin"
            ringtone_name = self._builtin_combo.currentText()
            ringtone_key = ringtone_name
            custom_path = None

        return Schedule(
            id=self._editing_schedule_id or 0,
            content=self._content_edit.toPlainText(),
            hour=self._hour_spin.value(),
            minute=self._minute_spin.value(),
            ringtone_name=ringtone_name,
            ringtone_key=ringtone_key,
            ringtone_type=ringtone_type,
            custom_ringtone_path=custom_path,
            content_color=content_color,
            content_font_size=int(self._font_combo.currentText()),
        )

    def _resolve_content_color(self) -> str:
        """Return the hex color for the current content color selection."""
        name = self._color_combo.currentText()
        hex_color = COLOR_NAMES.get(name, "#000000")
        if hex_color == "custom":
            return self._custom_color
        return hex_color

    # ── Public methods ─────────────────────────────────────────────────────

    def set_editing_schedule(self, schedule: Schedule) -> None:
        """Load an existing schedule into the form for editing."""
        self._editing_schedule_id = schedule.id

        self._content_edit.setPlainText(schedule.content)
        self._hour_spin.setValue(schedule.hour)
        self._minute_spin.setValue(schedule.minute)

        # Restore ringtone state
        if schedule.ringtone_type == "custom" and schedule.custom_ringtone_path:
            self._custom_ringtone_path = schedule.custom_ringtone_path
            from pathlib import Path
            filename = Path(schedule.custom_ringtone_path).name
            self._custom_ringtone_label.setText(filename)
            self._custom_ringtone_label.setStyleSheet("color: #000;")
        else:
            self._custom_ringtone_path = None
            self._custom_ringtone_label.setText("未选择文件")
            self._custom_ringtone_label.setStyleSheet("color: #666;")
            # Set builtin combo — only if the name is in our list
            index = self._builtin_combo.findText(schedule.ringtone_name)
            if index >= 0:
                self._builtin_combo.setCurrentIndex(index)

        # Restore color
        self.set_content_color(schedule.content_color)

        # Restore font size
        self.set_content_font_size(schedule.content_font_size)

        # Update button text
        self._save_btn.setText("保存修改")

    def clear_form(self) -> None:
        """Reset all form fields to defaults."""
        self._editing_schedule_id = None
        self._custom_ringtone_path = None
        self._custom_color = "#000000"

        self._content_edit.clear()
        self._hour_spin.setValue(DEFAULT_HOUR)
        self._minute_spin.setValue(DEFAULT_MINUTE)

        # Reset color
        self._color_combo.blockSignals(True)
        self._color_combo.setCurrentText(DEFAULT_COLOR_NAME)
        self._color_combo.blockSignals(False)
        self._color_preview.setStyleSheet(
            f"background-color: {COLOR_NAMES[DEFAULT_COLOR_NAME]}; border: 1px solid #999;"
        )

        # Reset font size
        self._font_combo.setCurrentText(DEFAULT_FONT_SIZE)

        # Reset builtin ringtone
        self._builtin_combo.blockSignals(True)
        self._builtin_combo.setCurrentText(DEFAULT_BUILTIN_RINGTONE)
        self._builtin_combo.blockSignals(False)

        # Reset custom ringtone
        self._custom_ringtone_label.setText("未选择文件")
        self._custom_ringtone_label.setStyleSheet("color: #666;")

        # Reset button text
        self._save_btn.setText("添加日程")

    def get_form_data(self) -> dict:
        """Return current form values as a dict."""
        return {
            "content": self._content_edit.toPlainText(),
            "hour": self._hour_spin.value(),
            "minute": self._minute_spin.value(),
            "ringtone_name": self._builtin_combo.currentText(),
            "ringtone_type": "custom" if self._custom_ringtone_path else "builtin",
            "custom_ringtone_path": self._custom_ringtone_path,
            "content_color": self._resolve_content_color(),
            "content_font_size": int(self._font_combo.currentText()),
        }

    def set_colors(self, colors: dict) -> None:
        """Replace COLOR_NAMES and update the combo. (Unused but provided for API compat.)"""
        global COLOR_NAMES
        COLOR_NAMES.clear()
        COLOR_NAMES.update(colors)

        self._color_combo.blockSignals(True)
        self._color_combo.clear()
        self._color_combo.addItems(colors.keys())
        self._color_combo.setCurrentText(DEFAULT_COLOR_NAME if DEFAULT_COLOR_NAME in colors else list(colors.keys())[0])
        self._color_combo.blockSignals(False)

    def set_content_color(self, hex_color: str) -> None:
        """Set the content color picker and preview to a specific hex value."""
        # Try to match to a named color
        for name, hx in COLOR_NAMES.items():
            if hx.upper() == hex_color.upper() and hx != "custom":
                self._color_combo.blockSignals(True)
                self._color_combo.setCurrentText(name)
                self._color_combo.blockSignals(False)
                self._color_preview.setStyleSheet(
                    f"background-color: {hx}; border: 1px solid #999;"
                )
                return

        # Not found — treat as custom
        self._custom_color = hex_color
        self._color_combo.blockSignals(True)
        self._color_combo.setCurrentText("自定义颜色")
        self._color_combo.blockSignals(False)
        self._color_preview.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid #999;"
        )

    def set_content_font_size(self, size: int) -> None:
        """Set the font size combo to a specific value."""
        size_str = str(size)
        index = self._font_combo.findText(size_str)
        if index >= 0:
            self._font_combo.setCurrentIndex(index)

    def set_custom_ringtone_label(self, filename: str) -> None:
        """Update the custom ringtone display label."""
        self._custom_ringtone_label.setText(filename)
        self._custom_ringtone_label.setStyleSheet("color: #000;" if filename != "未选择文件" else "color: #666;")

    def set_builtin_ringtone(self, name: str) -> None:
        """Set the built-in ringtone combo to a specific name."""
        index = self._builtin_combo.findText(name)
        if index >= 0:
            self._builtin_combo.blockSignals(True)
            self._builtin_combo.setCurrentIndex(index)
            self._builtin_combo.blockSignals(False)


# ═══ notification ═══
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox,
    QFrame, QSizePolicy
)
import os
import sys

# Import models — adjust path for subpackage usage


def _make_circular_pixmap(path: str, size: int) -> QPixmap:
    """Load an image and return a circularly masked QPixmap at the given size."""
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return QPixmap()
    scaled = pixmap.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )
    # Create circular mask
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainter, QPainterPath
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path_obj = QPainterPath()
    path_obj.addEllipse(0, 0, size, size)
    painter.setClipPath(path_obj)
    # Center the scaled image
    x_offset = (scaled.width() - size) // 2
    y_offset = (scaled.height() - size) // 2
    painter.drawPixmap(-x_offset, -y_offset, scaled)
    painter.end()
    return result


class NotificationDialog(QDialog):
    """Frameless notification popup with fade animation, character display, and action buttons."""

    # Signal emitted when user clicks 延后; carries snooze minutes
    snoozed: pyqtSignal = pyqtSignal(int)
    # Signal emitted when user clicks "Get it" (close/acknowledge)
    closed: pyqtSignal = pyqtSignal()
    # Placeholder signal for the main app to connect audio playback
    play_ringtone_signal: pyqtSignal = pyqtSignal()

    # ── fixed layout constants ──────────────────────────────────
    DIALOG_WIDTH = 500
    AVATAR_SIZE = 100

    def __init__(self, parent, schedule: Schedule, settings: AppSettings):
        super().__init__(parent)

        self._schedule = schedule
        self._settings = settings

        # ── window flags ────────────────────────────────────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedWidth(self.DIALOG_WIDTH)
        self.setWindowOpacity(0.0)

        # ── stylesheet ──────────────────────────────────────────
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
                border: 1px solid #CCCCCC;
                border-radius: 8px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
            QPushButton {
                border: 1px solid #BBBBBB;
                border-radius: 4px;
                padding: 5px 16px;
                background-color: #E8E8E8;
                color: #333333;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
            QPushButton:pressed {
                background-color: #BBBBBB;
            }
            QSpinBox {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #BBBBBB;
                border-radius: 3px;
                padding: 3px 4px;
                font-size: 12px;
                max-width: 60px;
            }
        """)

        # ── build UI ────────────────────────────────────────────
        self._build_ui()
        self._adjust_height()

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # ── character row ───────────────────────────────────────
        char_row = QHBoxLayout()
        char_row.setSpacing(12)

        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(self.AVATAR_SIZE, self.AVATAR_SIZE)
        self._load_avatar()
        char_row.addWidget(self._avatar_label)

        self._name_label = QLabel(self._settings.character_name)
        self._name_label.setFont(self._make_font(
            self._settings.character_name_font_size, bold=True
        ))
        self._name_label.setStyleSheet(
            f"color: {self._settings.character_name_color};"
        )
        self._name_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        char_row.addWidget(self._name_label, 1)

        root.addLayout(char_row)

        # ── message area ────────────────────────────────────────
        time_str = f"{self._schedule.hour:02d}:{self._schedule.minute:02d}"
        message_text = f"时间: {time_str}\n\n{self._schedule.content}"

        self._message_label = QLabel(message_text)
        self._message_label.setWordWrap(True)
        self._message_label.setFont(self._make_font(
            self._schedule.content_font_size
        ))
        self._message_label.setStyleSheet(
            f"color: {self._schedule.content_color};"
            "background-color: #F5F5DC;"
            "border-radius: 4px;"
            "padding: 12px;"
        )
        self._message_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        root.addWidget(self._message_label, 1)

        # ── button row ──────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        # Left – snooze
        snooze_label = QLabel("延后(分钟):")
        snooze_label.setStyleSheet("color: #666666; font-size: 13px;")
        btn_row.addWidget(snooze_label)

        self._snooze_spin = QSpinBox()
        self._snooze_spin.setRange(1, 120)
        self._snooze_spin.setValue(self._settings.default_snooze_minutes)
        btn_row.addWidget(self._snooze_spin)

        snooze_btn = QPushButton("延后")
        snooze_btn.clicked.connect(self._on_snooze)
        btn_row.addWidget(snooze_btn)

        btn_row.addStretch()

        # Right – Get it
        getit_btn = QPushButton("Get it")
        getit_btn.clicked.connect(self._on_close)
        btn_row.addWidget(getit_btn)

        root.addLayout(btn_row)

    def _adjust_height(self):
        """Size the dialog to fit its content, then fix the height."""
        # Let the layout compute its size hint
        self.adjustSize()
        hint = self.sizeHint()
        height = max(hint.height(), 280)
        self.setFixedSize(self.DIALOG_WIDTH, height)

    # ── avatar loading ──────────────────────────────────────────

    def _load_avatar(self):
        path = self._settings.character_avatar_path
        if path and os.path.exists(path):
            circular = _make_circular_pixmap(path, self.AVATAR_SIZE)
            if not circular.isNull():
                self._avatar_label.setPixmap(circular)
                return
        # Default: empty placeholder
        self._avatar_label.setText("")
        self._avatar_label.setStyleSheet(
            "background-color: #DDDDDD; border-radius: 50px;"
        )

    # ── font helper ─────────────────────────────────────────────

    @staticmethod
    def _make_font(size: int, bold: bool = False) -> QFont:
        font = QFont("Microsoft YaHei", size)
        font.setBold(bold)
        return font

    # ── show / animation ────────────────────────────────────────

    def showEvent(self, event):
        """Position at bottom-right and start fade-in."""
        super().showEvent(event)
        self._position_bottom_right()
        self._fade_in()

    def _position_bottom_right(self):
        screen = self.screen()
        if screen is None:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        x = avail.right() - self.DIALOG_WIDTH - 20
        y = avail.bottom() - self.height() - 40
        self.move(x, y)

    def _fade_in(self):
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def fade_out(self, on_finished=None):
        """Animate opacity to 0 over 250 ms, then call on_finished."""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(250)
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        if on_finished:
            self._fade_anim.finished.connect(on_finished)
        self._fade_anim.start()

    # ── button handlers ─────────────────────────────────────────

    def _on_snooze(self):
        minutes = self._snooze_spin.value()
        self.fade_out(on_finished=lambda: self._finish_snooze(minutes))

    def _finish_snooze(self, minutes: int):
        self.snoozed.emit(minutes)
        self.accept()

    def _on_close(self):
        self.fade_out(on_finished=self._finish_close)

    def _finish_close(self):
        self.closed.emit()
        self.accept()

    # ── block normal close (Esc / Alt+F4 / title-bar ×) ────────

    def reject(self):
        """Swallow reject events — the user MUST use the buttons."""
        pass


# ═══ settings ═══
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QRadioButton, QButtonGroup,
    QFileDialog, QColorDialog, QWidget, QSizePolicy,
)


COLOR_NAMES = {
    "黑色": "#000000",
    "深灰色": "#333333",
    "蓝色": "#0000FF",
    "绿色": "#008000",
    "红色": "#FF0000",
    "棕色": "#8B4513",
    "紫色": "#800080",
    "橙色": "#FFA500",
    "自定义颜色": "custom",
}

NAME_FONT_SIZES = ["12", "14", "16", "18", "20", "24"]

AVATAR_SIZE = 100

_IMAGE_FILTER = "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"


class SettingsDialog(QDialog):
    """Modal dialog for editing application settings."""

    def __init__(self, parent, settings: AppSettings,
                 avatar_pixmap: QPixmap | None = None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumWidth(460)

        self._settings = settings
        self._avatar_pixmap = avatar_pixmap
        self._avatar_path = settings.character_avatar_path

        self._build_ui()
        self._load_settings()

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(self._build_character_group())
        layout.addWidget(self._build_reminder_group())
        layout.addWidget(self._build_close_behavior_group())
        layout.addStretch()
        layout.addLayout(self._build_button_row())

    # ── 角色设置 ─────────────────────────────────────────────────

    def _build_character_group(self) -> QGroupBox:
        group = QGroupBox("角色设置")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 角色名称
        self._name_edit = QLineEdit()
        form.addRow("角色名称:", self._name_edit)

        # 名称颜色 + 预览
        self._color_combo = QComboBox()
        self._color_combo.addItems(COLOR_NAMES.keys())
        self._color_combo.currentTextChanged.connect(self._on_color_combo_changed)

        self._color_preview = QLabel()
        self._color_preview.setFixedSize(20, 20)
        self._color_preview.setStyleSheet("border: 1px solid #999;")

        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        color_row.addWidget(self._color_combo)
        color_row.addWidget(self._color_preview)
        color_row.addStretch()
        form.addRow("名称颜色:", color_row)

        # 名称字体
        self._font_combo = QComboBox()
        self._font_combo.addItems(NAME_FONT_SIZES)
        form.addRow("名称字体:", self._font_combo)

        # 角色头像
        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_label.setStyleSheet(
            "border: 1px dashed #999; background: #f0f0f0;"
        )
        self._avatar_label.setText("无头像")

        choose_btn = QPushButton("选择")
        choose_btn.clicked.connect(self._on_choose_avatar)
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self._on_clear_avatar)

        avatar_btns = QVBoxLayout()
        avatar_btns.addWidget(choose_btn)
        avatar_btns.addWidget(clear_btn)
        avatar_btns.addStretch()

        avatar_row = QHBoxLayout()
        avatar_row.setContentsMargins(0, 0, 0, 0)
        avatar_row.addWidget(self._avatar_label)
        avatar_row.addLayout(avatar_btns)
        avatar_row.addStretch()
        form.addRow("角色头像:", avatar_row)

        return group

    # ── 提醒设置 ─────────────────────────────────────────────────

    def _build_reminder_group(self) -> QGroupBox:
        group = QGroupBox("提醒设置")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._snooze_spin = QSpinBox()
        self._snooze_spin.setRange(1, 120)
        self._snooze_spin.setSuffix(" 分钟")
        form.addRow("默认延后时间(分钟):", self._snooze_spin)

        from PyQt6.QtWidgets import QCheckBox
        self._catch_up_check = QCheckBox("应用休眠/关闭期间，补提醒错过的日程")
        self._catch_up_check.setChecked(True)
        form.addRow("", self._catch_up_check)
        return group

    # ── 关闭行为 ─────────────────────────────────────────────────

    def _build_close_behavior_group(self) -> QGroupBox:
        group = QGroupBox("关闭行为设置")
        layout = QVBoxLayout(group)

        self._behavior_group = QButtonGroup(self)

        self._tray_radio = QRadioButton("关闭时最小化到系统托盘")
        self._quit_radio = QRadioButton("关闭时退出应用")

        self._behavior_group.addButton(self._tray_radio)
        self._behavior_group.addButton(self._quit_radio)

        layout.addWidget(self._tray_radio)
        layout.addWidget(self._quit_radio)

        return group

    # ── Bottom buttons ───────────────────────────────────────────

    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        reset_btn = QPushButton("重置为默认值")
        reset_btn.clicked.connect(self.reset_to_defaults)

        save_btn = QPushButton("保存并返回")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)

        row.addWidget(reset_btn)
        row.addStretch()
        row.addWidget(save_btn)

        return row

    # ── Load / reset ─────────────────────────────────────────────

    def _load_settings(self):
        s = self._settings

        # 角色名称
        self._name_edit.setText(s.character_name)

        # 颜色
        color_name = self._resolve_color_name(s.character_name_color)
        # Temporarily block signal to avoid triggering dialog
        self._color_combo.blockSignals(True)
        self._color_combo.setCurrentText(color_name)
        self._color_combo.blockSignals(False)
        self._update_color_preview(s.character_name_color)

        # 字体
        font_str = str(s.character_name_font_size)
        if font_str in NAME_FONT_SIZES:
            self._font_combo.setCurrentText(font_str)
        else:
            self._font_combo.setCurrentIndex(0)

        # 头像
        self._refresh_avatar_preview()

        # 延后时间
        self._snooze_spin.setValue(s.default_snooze_minutes)

        # 补提醒
        self._catch_up_check.setChecked(s.catch_up_missed)


        # 关闭行为
        if s.close_behavior == "minimize_to_tray":
            self._tray_radio.setChecked(True)
        else:
            self._quit_radio.setChecked(True)

    def reset_to_defaults(self):
        """Reset all fields to application defaults."""
        defaults = AppSettings()

        self._name_edit.setText(defaults.character_name)

        self._color_combo.blockSignals(True)
        self._color_combo.setCurrentText(
            self._resolve_color_name(defaults.character_name_color))
        self._color_combo.blockSignals(False)
        self._update_color_preview(defaults.character_name_color)

        self._font_combo.setCurrentText(str(defaults.character_name_font_size))

        self._avatar_pixmap = None
        self._avatar_path = None
        self._refresh_avatar_preview()

        self._snooze_spin.setValue(defaults.default_snooze_minutes)

        if defaults.close_behavior == "minimize_to_tray":
            self._tray_radio.setChecked(True)
        else:
            self._quit_radio.setChecked(True)
        self._catch_up_check.setChecked(defaults.catch_up_missed)

    # ── Color helpers ────────────────────────────────────────────

    def _resolve_color_name(self, hex_color: str) -> str:
        """Map a hex color to a COLOR_NAMES key, or '自定义颜色'."""
        for name, value in COLOR_NAMES.items():
            if value.lower() == hex_color.lower():
                return name
        return "自定义颜色"

    def _update_color_preview(self, hex_color: str):
        """Fill the color preview swatch with the given hex color."""
        pm = QPixmap(20, 20)
        pm.fill(QColor(hex_color))
        self._color_preview.setPixmap(pm)

    def _on_color_combo_changed(self, text: str):
        value = COLOR_NAMES.get(text, "custom")
        if value == "custom":
            current = QColor(self._settings.custom_name_color)
            color = QColorDialog.getColor(current, self, "选择自定义颜色")
            if color.isValid():
                self._settings.custom_name_color = color.name()
                self._update_color_preview(color.name())
            else:
                # User cancelled; revert combo to the current effective color
                self._color_combo.blockSignals(True)
                self._color_combo.setCurrentText(
                    self._resolve_color_name(self._settings.character_name_color))
                self._color_combo.blockSignals(False)
        else:
            self._update_color_preview(value)

    # ── Avatar helpers ───────────────────────────────────────────

    def _on_choose_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择头像图片", "",
            _IMAGE_FILTER,
        )
        if not path:
            return

        cropper = AvatarCropper(self, path)
        if cropper.exec() == QDialog.DialogCode.Accepted:
            pixmap, filename, _ = cropper.get_result()
            if pixmap and filename:
                self._avatar_pixmap = pixmap
                self._avatar_path = filename
                self._refresh_avatar_preview()

    def _on_clear_avatar(self):
        self._avatar_pixmap = None
        self._avatar_path = None
        self._refresh_avatar_preview()

    def _refresh_avatar_preview(self):
        if self._avatar_pixmap and not self._avatar_pixmap.isNull():
            scaled = self._avatar_pixmap.scaled(
                AVATAR_SIZE, AVATAR_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._avatar_label.setPixmap(scaled)
            self._avatar_label.setText("")
        else:
            self._avatar_label.clear()
            self._avatar_label.setText("无头像")

    # ── Result ───────────────────────────────────────────────────

    def get_settings(self) -> AppSettings:
        """Return an AppSettings reflecting the current form state."""
        s = self._settings

        s.character_name = self._name_edit.text().strip()

        # Resolve effective color from combo
        color_key = self._color_combo.currentText()
        if color_key == "自定义颜色":
            s.character_name_color = s.custom_name_color
        else:
            s.character_name_color = COLOR_NAMES.get(
                color_key, s.character_name_color)

        s.character_name_font_size = int(self._font_combo.currentText())
        s.character_avatar_path = self._avatar_path
        s.default_snooze_minutes = self._snooze_spin.value()
        s.catch_up_missed = self._catch_up_check.isChecked()

        if self._tray_radio.isChecked():
            s.close_behavior = "minimize_to_tray"
        else:
            s.close_behavior = "quit_application"

        return s

    def get_result(self):
        """Return (AppSettings, QPixmap|None) for use by the caller."""
        return self.get_settings(), self._avatar_pixmap


# ═══ app ═══
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import pygame
from PIL import Image, ImageDraw, ImageQt

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QSystemTrayIcon, QMenu,
    QStyle, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPixmap



# --- Reminder Thread ---
class ReminderThread(QThread):
    """Background thread that checks schedules and emits signals for due reminders."""
    reminder_due = pyqtSignal(Schedule)

    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self._app = app_ref
        self._running = True
        self._last_check = datetime.now()

    def run(self):
        while self._running:
            now = datetime.now()
            gap = (now - self._last_check).total_seconds()

            # Catch-up: if gap is large (> 120 seconds), system may have slept
            if gap > 120 and self._app.settings.catch_up_missed:
                self._catch_up_missed(now)

            self._last_check = now

            for schedule in self._app.settings.schedules:
                if not schedule.active:
                    continue

                # Skip if snoozed
                if schedule.snoozed_until:
                    try:
                        snoozed = datetime.fromisoformat(schedule.snoozed_until)
                        if now < snoozed:
                            continue
                        else:
                            schedule.snoozed_until = None
                    except (ValueError, TypeError):
                        schedule.snoozed_until = None

                # Check time match (within first 5 seconds of the minute)
                current_time = now.time()
                if (current_time.hour == schedule.hour
                        and current_time.minute == schedule.minute
                        and 0 <= current_time.second < 5):
                    last = schedule.last_triggered
                    if last is None or (now - datetime.fromisoformat(last)).total_seconds() > 55:
                        schedule.last_triggered = now.isoformat()
                        self.reminder_due.emit(schedule)

            self.msleep(1000)

    def _catch_up_missed(self, now: datetime):
        """Check for schedules that should have fired during the gap."""
        for schedule in self._app.settings.schedules:
            if not schedule.active:
                continue
            if schedule.snoozed_until:
                try:
                    if now < datetime.fromisoformat(schedule.snoozed_until):
                        continue
                except (ValueError, TypeError):
                    pass

            # Check if schedule time fell within the gap
            schedule_time = now.replace(hour=schedule.hour, minute=schedule.minute, second=0, microsecond=0)
            if self._last_check < schedule_time <= now:
                # Check not already triggered today
                last = schedule.last_triggered
                if last is None or datetime.fromisoformat(last).date() < now.date():
                    schedule.last_triggered = now.isoformat()
                    self.reminder_due.emit(schedule)

    def stop(self):
        self._running = False


# --- Main Application ---
class GetItApp(QMainWindow):
    """Main window orchestrating all widgets."""

    def __init__(self, start_minimized: bool = False):
        super().__init__()
        self.setWindowTitle("Get It")
        self.setMinimumSize(520, 650)
        self.resize(520, 700)

        # Icon
        if os.path.exists(_icon_path()):
            self.setWindowIcon(QIcon(_icon_path()))

        # --- Data ---
        self.data_manager = DataManager()
        self.settings = self.data_manager.load()

        # --- Audio ---
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        self.ringtones: dict = {}
        self._create_builtin_ringtones()
        self._load_custom_ringtones()

        # --- State ---
        self.editing_schedule_id: Optional[int] = None
        self.custom_ringtone_path: Optional[str] = None
        self.avatar_pixmap: Optional[QPixmap] = None
        self.notification_dialog: Optional[NotificationDialog] = None

        # --- Load avatar ---
        self._load_avatar()

        # --- UI ---
        self._create_central_widget()
        self._create_tray_icon()

        # --- IPC: single-instance wake-up ---
        self._ipc_server = QLocalServer(self)
        self._ipc_server.listen("GetItAppIPC")
        self._ipc_server.newConnection.connect(self._restore_from_tray)

        # --- Reminder Thread ---
        self.reminder_thread = ReminderThread(self)
        self.reminder_thread.reminder_due.connect(self._on_reminder_due)
        self.reminder_thread.start()

        # --- Close behavior ---
        if start_minimized:
            QTimer.singleShot(100, self._minimize_to_tray)

    # ========================
    # Audio
    # ========================
    def _create_builtin_ringtones(self):
        try:
            self.ringtones.update({
                "叮咚声": RingtoneGenerator.create_dingdong(),
                "风铃声": RingtoneGenerator.create_chime(),
                "蜂鸣声": RingtoneGenerator.create_beep(),
                "警报声": RingtoneGenerator.create_alert(),
                "通知音": RingtoneGenerator.create_notification(),
                "钢琴音": RingtoneGenerator.create_piano(),
                "合成器": RingtoneGenerator.create_synth(),
            })
        except Exception as e:
            print(f"创建内置铃声出错: {e}")

    def _load_custom_ringtones(self):
        for s in self.settings.schedules:
            if s.ringtone_type == "custom" and s.custom_ringtone_path:
                if os.path.exists(s.custom_ringtone_path) and s.ringtone_key not in self.ringtones:
                    try:
                        self.ringtones[s.ringtone_key] = pygame.mixer.Sound(s.custom_ringtone_path)
                    except Exception as e:
                        print(f"加载自定义铃声出错: {e}")

    def _play_ringtone(self, schedule: Schedule):
        key = schedule.ringtone_key
        if key in self.ringtones:
            try:
                pygame.mixer.stop()
                self.ringtones[key].play()
            except Exception:
                if "风铃声" in self.ringtones:
                    pygame.mixer.stop()
                    self.ringtones["风铃声"].play()

    def _stop_ringtone(self):
        pygame.mixer.stop()

    # ========================
    # Avatar
    # ========================
    def _load_avatar(self):
        path = self.settings.character_avatar_path
        if path and os.path.exists(path):
            try:
                img = Image.open(path)
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                mask = Image.new('L', (100, 100), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
                result = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
                result.putalpha(mask)
                result.paste(img, (0, 0), mask)
                self.avatar_pixmap = QPixmap.fromImage(ImageQt.ImageQt(result))
            except Exception as e:
                print(f"加载头像出错: {e}")
                self.avatar_pixmap = None

    # ========================
    # System Tray
    # ========================
    def _create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(_icon_path()):
            self.tray_icon.setIcon(QIcon(_icon_path()))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        menu = QMenu()
        show_action = QAction("打开主界面", self)
        show_action.triggered.connect(self._restore_from_tray)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_application)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_from_tray()

    def _minimize_to_tray(self):
        self.hide()
        self.status_label.setText("应用已最小化到系统托盘")

    def _restore_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.status_label.setText("应用已恢复")

    def _quit_application(self):
        self._stop_ringtone()
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        self.reminder_thread.stop()
        self.reminder_thread.wait(2000)
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if self.settings.close_behavior == "minimize_to_tray":
            event.ignore()
            self._minimize_to_tray()
        else:
            self._quit_application()

    # ========================
    # Main UI
    # ========================
    def _create_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # --- Top bar ---
        top_bar = QHBoxLayout()
        btn_settings = QPushButton("⚙")
        btn_settings.setFixedWidth(40)
        btn_settings.clicked.connect(self._show_settings)
        top_bar.addWidget(btn_settings)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # --- Schedule Editor ---
        self.editor = ScheduleEditor()
        self.editor.schedule_saved.connect(self._on_schedule_saved)
        self.editor.test_notification_requested.connect(self._on_test_notification)
        self.editor.preview_builtin_ringtone.connect(self._on_preview_builtin)
        self.editor.custom_ringtone_selected.connect(self._on_custom_ringtone_selected)
        self.editor.preview_custom_ringtone.connect(self._on_preview_custom)
        self.editor.stop_preview.connect(self._stop_ringtone)
        main_layout.addWidget(self.editor)

        # --- Schedule List ---
        self.schedule_list = ScheduleListWidget()
        self.schedule_list.schedule_selected.connect(self._on_schedule_selected)
        self.schedule_list.schedule_deleted.connect(self._on_schedule_deleted)
        self.schedule_list.new_schedule_requested.connect(self._on_new_schedule)
        self.schedule_list.refresh(self.settings.schedules)
        main_layout.addWidget(self.schedule_list)

        # --- Status bar ---
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("padding: 4px; background: #e0e0e0; border: 1px solid #ccc;")
        main_layout.addWidget(self.status_label)

    # ========================
    # Schedule CRUD
    # ========================
    def _on_schedule_saved(self, schedule: Schedule):
        """Save or update a schedule from editor."""
        # Assign ID for new schedules
        if schedule.id == 0 or schedule.id is None:
            schedule.id = max((s.id for s in self.settings.schedules), default=0) + 1
            schedule.snoozed_until = None
            schedule.last_triggered = None
            self.settings.schedules.append(schedule)
            self.status_label.setText(f"已添加日程: {schedule.hour:02d}:{schedule.minute:02d}")
        else:
            # Update existing
            for s in self.settings.schedules:
                if s.id == schedule.id:
                    s.content = schedule.content
                    s.hour = schedule.hour
                    s.minute = schedule.minute
                    s.ringtone_name = schedule.ringtone_name
                    s.ringtone_key = schedule.ringtone_key
                    s.ringtone_type = schedule.ringtone_type
                    s.custom_ringtone_path = schedule.custom_ringtone_path
                    s.content_color = schedule.content_color
                    s.content_font_size = schedule.content_font_size
                    break
            self.status_label.setText(f"已修改日程: {schedule.hour:02d}:{schedule.minute:02d}")

        self._refresh_and_save()
        self.editor.clear_form()
        self.editing_schedule_id = None

    def _on_schedule_selected(self, schedule: Schedule):
        self.editor.set_editing_schedule(schedule)
        self.editing_schedule_id = schedule.id

    def _on_new_schedule(self):
        """Clear form and deselect list to enter add mode."""
        self.editor.clear_form()
        self.editing_schedule_id = None
        self.schedule_list.clear_selection()

    def _on_schedule_deleted(self, schedule: Schedule):
        self.settings.schedules = [s for s in self.settings.schedules if s.id != schedule.id]
        if self.editing_schedule_id == schedule.id:
            self.editor.clear_form()
            self.editing_schedule_id = None
        self._refresh_and_save()
        self.status_label.setText(f"已删除日程: {schedule.hour:02d}:{schedule.minute:02d}")

    def _refresh_and_save(self):
        self.schedule_list.refresh(self.settings.schedules)
        self.data_manager.save(self.settings)

    # ========================
    # Ringtone previews
    # ========================
    def _on_preview_builtin(self, name: str):
        if name in self.ringtones:
            self._stop_ringtone()
            self.ringtones[name].play()
            self.status_label.setText(f"试听: {name}")

    def _on_preview_custom(self, filepath: str):
        key = os.path.basename(filepath)
        if key in self.ringtones:
            self._stop_ringtone()
            self.ringtones[key].play()

    def _on_custom_ringtone_selected(self, filepath: str):
        if filepath and os.path.exists(filepath):
            try:
                sound = pygame.mixer.Sound(filepath)
                key = os.path.basename(filepath)
                self.ringtones[key] = sound
                self.custom_ringtone_path = filepath
                self.status_label.setText(f"已加载自定义铃声: {key}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载音频文件: {e}")

    # ========================
    # Test notification
    # ========================
    def _on_test_notification(self, schedule: Schedule):
        test_schedule = Schedule(
            id=0, content=schedule.content,
            hour=datetime.now().hour, minute=datetime.now().minute,
            ringtone_name=schedule.ringtone_name,
            ringtone_key=schedule.ringtone_key,
            ringtone_type=schedule.ringtone_type,
            content_color=schedule.content_color,
            content_font_size=schedule.content_font_size,
        )
        self._show_notification(test_schedule)

    # ========================
    # Notification dialog
    # ========================
    def _on_reminder_due(self, schedule: Schedule):
        self._show_notification(schedule)

    def _show_notification(self, schedule: Schedule):
        if self.notification_dialog and self.notification_dialog.isVisible():
            self.notification_dialog.close()

        dlg = NotificationDialog(None, schedule, self.settings)
        dlg.snoozed.connect(lambda mins: self._on_snooze(schedule, mins, dlg))
        dlg.closed.connect(lambda: self._on_dismiss(schedule, dlg))
        dlg.play_ringtone_signal.connect(lambda: self._play_ringtone(schedule))

        self.notification_dialog = dlg
        dlg.show()
        self._play_ringtone(schedule)

    def _on_snooze(self, schedule: Schedule, minutes: int, dialog):
        """BUG FIX: set snoozed_until without changing schedule hour/minute."""
        self._stop_ringtone()
        schedule.snoozed_until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        schedule.last_triggered = None
        self._refresh_and_save()
        new_time = datetime.now() + timedelta(minutes=minutes)
        self.status_label.setText(
            f"日程已延后 {minutes} 分钟，将在 {new_time:%H:%M} 再次提醒"
        )

    def _on_dismiss(self, schedule: Schedule, dialog):
        """Handle 'Get it' (dismiss)."""
        self._stop_ringtone()
        schedule.snoozed_until = None
        self._refresh_and_save()
        self.status_label.setText("日程已完成")

    # ========================
    # Settings dialog
    # ========================
    def _show_settings(self):
        dlg = SettingsDialog(self, self.settings, self.avatar_pixmap)
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            new_settings, new_avatar = dlg.get_result()
            self.settings = new_settings
            if new_avatar is not None:
                self.avatar_pixmap = new_avatar
            self.data_manager.save(self.settings)
            self.status_label.setText("设置已保存")


# ========================
# Entry point
# ========================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Get It")
    app.setQuitOnLastWindowClosed(False)

    # ── Single-instance: wake existing window silently ──
    shared = QSharedMemory("GetItAppSingleton")
    if shared.attach() or not shared.create(1):
        # Another instance running → tell it to show, then exit
        sock = QLocalSocket()
        sock.connectToServer("GetItAppIPC")
        if sock.waitForConnected(500):
            sock.disconnectFromServer()
        sys.exit(0)

    start_minimized = "--minimized" in sys.argv
    window = GetItApp(start_minimized=start_minimized)

    if not start_minimized:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
