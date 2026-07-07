"""Notification popup dialog for "Get It" daily reminder app.

A frameless, always-on-top QDialog positioned at the bottom-right of the screen
with fade-in/fade-out animations, character display, message area, and snooze/close buttons.
"""

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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Schedule, AppSettings


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
                background-color: #2C2C2C;
                border: 1px solid #555555;
                border-radius: 8px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
            QPushButton {
                border: 1px solid #777777;
                border-radius: 4px;
                padding: 5px 16px;
                background-color: #444444;
                color: #E0E0E0;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
            QSpinBox {
                background-color: #444444;
                color: #E0E0E0;
                border: 1px solid #777777;
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
        snooze_label.setStyleSheet("color: #CCCCCC; font-size: 13px;")
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
            "background-color: #444444; border-radius: 50px;"
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
