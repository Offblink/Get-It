"""AvatarCropper - PyQt6 circular avatar crop dialog."""
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
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icon.ico")
        try:
            if os.path.exists(icon_path):
                from PyQt6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
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
