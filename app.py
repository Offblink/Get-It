"""Get It — Daily Reminder Application (PyQt6).

Main application class that orchestrates all widgets, dialogs, audio, and the reminder thread.
"""
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

from models import Schedule, AppSettings
from data_manager import DataManager
from ringtone import RingtoneGenerator
from widgets.schedule_editor import ScheduleEditor
from widgets.schedule_list import ScheduleListWidget
from widgets.avatar_cropper import AvatarCropper
from dialogs.notification import NotificationDialog
from dialogs.settings import SettingsDialog


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
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

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
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
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

    start_minimized = "--minimized" in sys.argv
    window = GetItApp(start_minimized=start_minimized)

    if not start_minimized:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
