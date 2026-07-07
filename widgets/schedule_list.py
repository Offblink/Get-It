"""Schedule list widget for "Get It" daily reminder app."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import pyqtSignal, Qt

from models import Schedule


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._schedules: list[Schedule] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("今日日程")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

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
