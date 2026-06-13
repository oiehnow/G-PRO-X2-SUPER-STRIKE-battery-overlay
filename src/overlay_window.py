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

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)
        self._layout.setSpacing(4)

        # 기기 행들을 담는 컨테이너(매 갱신마다 다시 빌드)
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)
        self._build_message("🔋 --", "기기 검색 중…")

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

        self._layout.addWidget(self._rows_container)
        self._layout.addWidget(self.opacity_slider)

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

    # ---- 행 빌드 ----
    def _clear_rows(self):
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _add_device_row(self, name: str, percent: float, hours_text: str):
        title = QLabel(f"🔋 {name}  {percent:.0f}%")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")

        sub = QLabel(f"남은시간 {hours_text}")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: #cfd3dc;")

        row = QWidget()
        box = QVBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        box.addWidget(title)
        box.addWidget(sub)
        self._rows_layout.addWidget(row)

    def _build_message(self, title_text: str, sub_text: str):
        self._clear_rows()
        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        sub = QLabel(sub_text)
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: #cfd3dc;")
        self._rows_layout.addWidget(title)
        self._rows_layout.addWidget(sub)

    # ---- 상태 갱신 ----
    def update_devices(self, rows, error=None, setup=None):
        """rows: [{name, percent, hours_text}, ...] (온라인 기기만)."""
        if setup:
            self._build_message("⏳ 준비 중", setup)
        elif error:
            self._build_message("⚠ 백엔드 미연결", "LGSTrayEx 실행 확인")
        elif not rows:
            self._build_message("🔌 기기 없음", "연결된 기기를 켜 주세요")
        else:
            self._clear_rows()
            for r in rows:
                self._add_device_row(r["name"], r["percent"], r["hours_text"])
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
