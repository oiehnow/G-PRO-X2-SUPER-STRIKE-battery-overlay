"""앱 설정을 config.json 으로 로드/저장한다."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass


def _config_dir() -> str:
    """config.json 위치. PyInstaller 로 묶인 exe 면 exe 옆, 아니면 프로젝트 루트."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG_DIR = _config_dir()
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class Settings:
    # LGSTrayEx HTTP 서버 주소/포트 (설치 후 appsettings.toml 의 [HTTPServer] 값과 맞춤)
    backend_host: str = "127.0.0.1"
    backend_port: int = 12321
    # 비우면 마우스 이름으로 자동 탐색. 특정 기기 고정 시 deviceID 입력.
    device_id: str = ""
    device_name_hint: str = "PRO X 2"  # 자동 탐색 시 이름 매칭 키워드

    poll_interval_seconds: int = 30
    full_life_hours: float = 75.0

    toggle_hotkey: str = "ctrl+alt+b"
    opacity: float = 0.85  # 0.1 ~ 1.0

    # 마지막 오버레이 위치
    pos_x: int = 40
    pos_y: int = 40

    def save(self, path: str = CONFIG_PATH) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str = CONFIG_PATH) -> "Settings":
        if not os.path.exists(path):
            s = cls()
            s.save(path)
            return s
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()
        valid = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**valid)
