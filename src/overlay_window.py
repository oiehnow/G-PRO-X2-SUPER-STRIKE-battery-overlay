"""프레임리스 / 반투명 / 항상 위 오버레이 창.

상단 우측에 최소화·종료 버튼, 하단에 투명도 조절 바를 둔다.
최소화 모드에서는 모델명·슬라이더를 숨기고 배터리 잔량 %만 보여준다.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class OverlayWindow(QWidget):
    def __init__(self, settings, on_settings_changed, on_quit):
        super().__init__()
        self._settings = settings
        self._on_settings_changed = on_settings_changed
        self._on_quit = on_quit
        self._drag_offset: QPoint | None = None
        self._minimized = False
        # 마지막 상태 보관 → 최소화 토글 시 다시 그린다.
        self._last_rows: list | None = None
        self._last_error = None
        self._last_setup = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # 작업표시줄에 안 뜸
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 8, 10, 10)
        self._layout.setSpacing(4)

        # 상단 버튼 줄 (우측 정렬): 최소화, 종료
        self._buttons_bar = QWidget()
        bar = QHBoxLayout(self._buttons_bar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(4)
        bar.addStretch(1)
        self._min_btn = self._make_button("–", "최소화", self.toggle_minimize)
        self._close_btn = self._make_button("×", "종료", self._on_quit)
        bar.addWidget(self._min_btn)
        bar.addWidget(self._close_btn)

        # 기기 행들을 담는 컨테이너(매 갱신마다 다시 빌드)
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)

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

        self._layout.addWidget(self._buttons_bar)
        self._layout.addWidget(self._rows_container)
        self._layout.addWidget(self.opacity_slider)

        self._build_message("🔋 --", "기기 검색 중…")

        self.setWindowOpacity(self._settings.opacity)
        self.move(self._settings.pos_x, self._settings.pos_y)
        self.adjustSize()

    def _make_button(self, text: str, tooltip: str, on_click) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(18, 18)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(on_click)
        btn.setStyleSheet(
            """
            QPushButton { color: #cfd3dc; background: transparent; border: none;
                font-size: 13px; font-weight: bold; }
            QPushButton:hover { color: white; background: rgba(255,255,255,0.15);
                border-radius: 4px; }
            """
        )
        return btn

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

    def _add_device_row(self, name: str, percent: float):
        row = QWidget()
        box = QVBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(1)

        if not self._minimized:
            # 윗줄: 모델명 (작게)
            model = QLabel(name)
            model.setFont(QFont("Segoe UI", 9))
            model.setStyleSheet("color: #9aa0ab;")
            box.addWidget(model)

        # 배터리 잔량 % (크게, 가장 중요)
        pct = QLabel(f"🔋 {percent:.0f}%")
        pct.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        pct.setStyleSheet("color: white;")
        box.addWidget(pct)

        self._rows_layout.addWidget(row)

    def _build_message(self, title_text: str, sub_text: str):
        self._clear_rows()
        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        self._rows_layout.addWidget(title)
        if not self._minimized:
            sub = QLabel(sub_text)
            sub.setFont(QFont("Segoe UI", 9))
            sub.setStyleSheet("color: #cfd3dc;")
            self._rows_layout.addWidget(sub)

    # ---- 상태 갱신 ----
    def update_devices(self, rows, error=None, setup=None):
        """rows: [{name, percent}, ...] (온라인 기기만)."""
        self._last_rows = rows
        self._last_error = error
        self._last_setup = setup
        self._render()

    def _render(self):
        if self._last_setup:
            self._build_message("⏳ 준비 중", self._last_setup)
        elif self._last_error:
            self._build_message("⚠ 백엔드 미연결", "LGSTrayEx 실행 확인")
        elif not self._last_rows:
            self._build_message("🔌 기기 없음", "연결된 기기를 켜 주세요")
        else:
            self._clear_rows()
            for r in self._last_rows:
                self._add_device_row(r["name"], r["percent"])
        # 최소화 시 슬라이더 숨김
        self.opacity_slider.setVisible(not self._minimized)
        self.adjustSize()

    def toggle_minimize(self):
        """최소화 모드 토글: 켜면 배터리 % 숫자만, 끄면 전체 정보."""
        self._minimized = not self._minimized
        self._min_btn.setText("▢" if self._minimized else "–")
        self._min_btn.setToolTip("복원" if self._minimized else "최소화")
        self._render()

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
