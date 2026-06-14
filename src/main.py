"""앱 진입점: 첫 실행 시 백엔드 자동 설치 → 폴링 + 오버레이 + 트레이 + 단축키."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QProgressDialog

import backend_setup
from backend_client import BackendClient, BackendError
from overlay_window import OverlayWindow
from settings import Settings
from tray import build_tray

try:
    import keyboard  # 전역 단축키 (관리자 권한 없이도 대부분 동작)
except Exception:  # pragma: no cover
    keyboard = None


class SetupWorker(QThread):
    """백엔드(LGSTrayEx) 설치/실행을 백그라운드에서 처리."""

    progress = pyqtSignal(int, str)
    done = pyqtSignal(bool)

    def __init__(self, host: str, port: int):
        super().__init__()
        self._host = host
        self._port = port

    def run(self):
        try:
            ok = backend_setup.ensure_backend(
                self._host, self._port,
                progress_cb=lambda pct, msg: self.progress.emit(pct, msg),
            )
        except Exception:
            ok = False
        self.done.emit(ok)


class App:
    def __init__(self):
        self.qt = QApplication(sys.argv)
        self.qt.setQuitOnLastWindowClosed(False)

        self.settings = Settings.load()
        self.client = BackendClient(self.settings.backend_host, self.settings.backend_port)

        self.overlay = OverlayWindow(self.settings, self._save_settings, self.quit)
        self.overlay.show()
        self.tray = build_tray(self.qt, self.overlay, self.quit)
        self._register_hotkey()

        self._got_first = False  # 첫 성공 폴링 전엔 빠르게 재시도
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)

        self._ensure_backend_then_start()

    # ---- 백엔드 자동 준비 ----
    def _ensure_backend_then_start(self):
        host, port = self.settings.backend_host, self.settings.backend_port
        if backend_setup.is_backend_running(host, port):
            self._start_polling()
            return

        self.overlay.update_devices([], setup="백엔드 준비 중…")
        self._dialog = QProgressDialog("백엔드(LGSTrayEx) 준비 중…", None, 0, 100)
        self._dialog.setWindowTitle("PRO X2 배터리 오버레이 — 첫 실행 설정")
        self._dialog.setCancelButton(None)
        self._dialog.setMinimumDuration(0)
        self._dialog.setAutoClose(False)
        self._dialog.setValue(0)
        self._dialog.show()

        self._worker = SetupWorker(host, port)
        self._worker.progress.connect(self._on_setup_progress)
        self._worker.done.connect(self._on_setup_done)
        self._worker.start()

    def _on_setup_progress(self, pct: int, msg: str):
        self._dialog.setLabelText(msg)
        self._dialog.setValue(pct)

    def _on_setup_done(self, ok: bool):
        self._dialog.close()
        if ok:
            self._start_polling()
        else:
            self.overlay.update_devices([], error=True)
            # 백엔드가 늦게 떠도 잡을 수 있게 폴링은 돌린다
            self._start_polling()

    def _start_polling(self):
        # 첫 성공 전엔 3초 간격으로 빠르게 시도 (백엔드 기동/마우스 인식 대기)
        self.timer.start(3000)
        QTimer.singleShot(300, self.poll)

    # ---- 설정 저장 ----
    def _save_settings(self):
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
            statuses = self.client.get_all_statuses()
        except BackendError:
            self.overlay.update_devices([], error=True)
            return

        online = [s for s in statuses if s.is_online]  # 오프라인 기기는 숨김
        rows = [{"name": s.name, "percent": s.percent} for s in online]
        self.overlay.update_devices(rows)

        if not self._got_first and rows:
            # 첫 성공 → 정상 폴링 주기로 전환
            self._got_first = True
            self.timer.start(max(5, self.settings.poll_interval_seconds) * 1000)

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
