"""앱 진입점: 폴링 타이머 + 오버레이 + 트레이 + 전역 단축키."""

from __future__ import annotations

import sys
import time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from backend_client import BackendClient, BackendError
from battery_estimator import BatteryEstimator, format_hours
from overlay_window import OverlayWindow
from settings import Settings
from tray import build_tray

try:
    import keyboard  # 전역 단축키 (관리자 권한 없이도 대부분 동작)
except Exception:  # pragma: no cover
    keyboard = None


class App:
    def __init__(self):
        self.qt = QApplication(sys.argv)
        self.qt.setQuitOnLastWindowClosed(False)

        self.settings = Settings.load()
        self.estimator = BatteryEstimator(full_life_hours=self.settings.full_life_hours)
        self.client = BackendClient(self.settings.backend_host, self.settings.backend_port)
        self._device_id = self.settings.device_id

        self.overlay = OverlayWindow(self.settings, self._save_settings)
        self.overlay.show()

        self.tray = build_tray(self.qt, self.overlay, self.quit)

        self._register_hotkey()

        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(max(5, self.settings.poll_interval_seconds) * 1000)
        QTimer.singleShot(500, self.poll)  # 즉시 한 번

    def _save_settings(self):
        self.settings.device_id = self._device_id
        self.settings.save()

    def _register_hotkey(self):
        if keyboard is None:
            return
        try:
            keyboard.add_hotkey(self.settings.toggle_hotkey, self.overlay.toggle)
        except Exception:
            pass  # 단축키 등록 실패해도 트레이로 토글 가능

    def poll(self):
        try:
            if not self._device_id:
                self._device_id = self.client.resolve_device_id(
                    self.settings.device_name_hint
                )
                self._save_settings()
            status = self.client.get_status(self._device_id)
        except BackendError:
            self.overlay.update_status(0, "", False, error=True)
            return

        self.estimator.add_sample(time.monotonic(), status.percent)
        hours = self.estimator.hours_remaining(status.percent)
        self.overlay.update_status(
            status.percent, format_hours(hours), status.is_online
        )

    def quit(self):
        self._save_settings()
        if keyboard is not None:
            try:
                keyboard.clear_all_hotkeys()
            except Exception:
                pass
        self.qt.quit()

    def run(self):
        sys.exit(self.qt.exec())


if __name__ == "__main__":
    App().run()
