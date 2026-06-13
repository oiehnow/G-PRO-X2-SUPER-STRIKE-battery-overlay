"""시스템 트레이 아이콘 및 메뉴."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from settings import APP_VERSION


def _make_icon() -> QIcon:
    """간단한 배터리 모양 아이콘을 코드로 그려 둔다(외부 파일 불필요)."""
    pm = QPixmap(32, 32)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(108, 196, 255))
    p.setPen(QColor(230, 230, 230))
    p.drawRoundedRect(6, 10, 18, 12, 2, 2)
    p.drawRect(24, 13, 3, 6)
    p.end()
    return QIcon(pm)


def build_tray(app, overlay, on_quit) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(_make_icon(), parent=app)
    tray.setToolTip(f"배터리 오버레이 v{APP_VERSION}")

    menu = QMenu()

    toggle_action = QAction("오버레이 표시/숨김", menu)
    toggle_action.triggered.connect(overlay.toggle)
    menu.addAction(toggle_action)

    menu.addSeparator()

    quit_action = QAction("종료", menu)
    quit_action.triggered.connect(on_quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: overlay.toggle()
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )
    tray.show()
    return tray
