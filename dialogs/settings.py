"""SettingsDialog - application settings editor."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QRadioButton, QButtonGroup,
    QFileDialog, QColorDialog, QWidget, QSizePolicy,
)

from models import AppSettings
from widgets.avatar_cropper import AvatarCropper

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
