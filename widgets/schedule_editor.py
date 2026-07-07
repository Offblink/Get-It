"""Schedule editor widget for the "Get It" daily reminder app."""

from PyQt6.QtWidgets import (
    QGroupBox, QLabel, QTextEdit, QComboBox, QSpinBox,
    QPushButton, QHBoxLayout, QVBoxLayout,
    QFileDialog, QColorDialog,
)
from PyQt6.QtCore import pyqtSignal

from models import Schedule

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
        self._hour_spin.setFixedWidth(60)
        time_layout.addWidget(self._hour_spin)

        time_layout.addWidget(QLabel(":"))

        self._minute_spin = ZPaddedSpinBox()
        self._minute_spin.setRange(0, 59)
        self._minute_spin.setValue(DEFAULT_MINUTE)
        self._minute_spin.setFixedWidth(60)
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
