"""프레임리스 / 반투명 / 항상 위 오버레이 창. 투명도 조절 바 포함."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import QSlider, QVBoxLayout, QLabel, QWidget


class OverlayWindow(QWidget):
    def __init__(self, settings, on_settings_changed):
        super().__init__()
        self._settings = settings
        self._on_settings_changed = on_settings_changed
        self._drag_offset: QPoint | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # 작업표시줄에 안 뜸
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self.battery_label = QLabel("🔋 --%")
        self.battery_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.battery_label.setStyleSheet("color: white;")

        self.time_label = QLabel("남은시간 --")
        self.time_label.setFont(QFont("Segoe UI", 9))
        self.time_label.setStyleSheet("color: #cfd3dc;")

        # 투명도 조절 바
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)  # 20%~100%
        self.opacity_slider.setValue(int(self._settings.opacity * 100))
        self.opacity_slider.setFixedHeight(14)
        self.opacity_slider.setToolTip("투명도")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_slider.setStyleSheet(
            """
            QSlider::groove:horizontal { height: 4px; background: #555; border-radius: 2px; }
            QSlider::handle:horizontal { width: 12px; background: #6cc4ff;
                margin: -5px 0; border-radius: 6px; }
            """
        )

        layout.addWidget(self.battery_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.opacity_slider)

        self.setWindowOpacity(self._settings.opacity)
        self.move(self._settings.pos_x, self._settings.pos_y)
        self.adjustSize()

    # ---- 렌더링: 둥근 반투명 배경 ----
    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 12, 12)
        painter.fillPath(path, QColor(20, 22, 28, 220))

    # ---- 상태 갱신 ----
    def update_status(self, percent, hours_text, is_online, error=None, setup=None):
        if setup:
            self.battery_label.setText("⏳ 준비 중")
            self.time_label.setText(setup)
            return
        if error:
            self.battery_label.setText("⚠ 백엔드 미연결")
            self.time_label.setText("LGSTrayEx 실행 확인")
            return
        icon = "🔋" if is_online else "💤"
        self.battery_label.setText(f"{icon} {percent:.0f}%")
        suffix = "" if is_online else " (오프라인)"
        self.time_label.setText(f"남은시간 {hours_text}{suffix}")
        self.adjustSize()

    def _on_opacity_changed(self, value: int):
        opacity = value / 100.0
        self.setWindowOpacity(opacity)
        self._settings.opacity = opacity
        self._on_settings_changed()

    # ---- 드래그 이동 ----
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_offset = None
        self._settings.pos_x = self.x()
        self._settings.pos_y = self.y()
        self._on_settings_changed()

    def toggle(self):
        self.setVisible(not self.isVisible())
