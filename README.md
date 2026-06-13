# PRO X2 Battery Overlay

<img width="396" height="232" alt="image" src="https://github.com/user-attachments/assets/ea0a7be8-f67a-44c0-9c1b-331005e4bb45" />


로지텍 **PRO X2 Superstrike**(및 기타 Logitech 무선 기기)의 배터리 잔량과 **예상 남은 사용 시간**을 작은 반투명 오버레이로 띄우는 Windows 앱입니다. 단축키로 켜고 끌 수 있고, **투명도 조절 바**가 내장되어 있습니다.

## 왜 별도 백엔드(LGSTrayEx)가 필요한가

PRO X2 라인은 표준 HID++ 가 아니라 신형 **Centurion 프로토콜**을 사용해 마우스와 직접 통신하기가 까다롭습니다. 그래서 이미 이 프로토콜을 구현한 오픈소스 트레이앱 **[LGSTrayEx](https://github.com/strain08/LGSTrayEx)** 가 노출하는 **로컬 HTTP/XML 엔드포인트**를 폴링합니다. 이 앱은 "예쁜 오버레이 + 토글 + 남은시간 계산"만 담당합니다.

> "남은 시간"은 마우스가 알려주지 않습니다. `(시각, 배터리%)` 샘플을 누적해 방전율(%/h)을 구하고 외삽합니다. 표본이 쌓이기 전에는 스펙 수명(기본 75h)을 기준으로 표시합니다.

## 설치 — 원클릭 (일반 사용자)

1. [Releases](https://github.com/oiehnow/G-PRO-X2-SUPER-STRIKE-battery-overlay/releases) 에서 **`ProX2BatteryOverlay.exe`** 를 받습니다.
2. **더블클릭.** 끝입니다.

처음 실행하면 앱이 백엔드(LGSTrayEx)가 없는 것을 감지하고 **자동으로 내려받아 설정·실행**합니다(약 1분, 진행바 표시). 이후부터는 즉시 배터리가 표시됩니다. `appsettings.toml` 을 직접 건드릴 필요가 없습니다.

> 백엔드(LGSTrayEx)는 GPL-3.0 별도 프로젝트라 동봉하지 않고, 첫 실행 시 [공식 릴리스](https://github.com/strain08/LGSTrayEx/releases)에서 `%LOCALAPPDATA%\ProX2BatteryOverlay\LGSTrayEx` 로 내려받습니다.

## 실행 — 소스에서 (개발자)

```powershell
pip install -r requirements.txt
python src/main.py
```

소스 실행도 동일하게 첫 실행 시 백엔드를 자동 준비합니다.

## 사용법

- 기본 단축키 **Ctrl+Alt+B** 로 오버레이 표시/숨김.
- 트레이 아이콘 좌클릭으로도 토글, 우클릭으로 메뉴(표시/숨김, 종료).
- 오버레이를 드래그해 위치 이동, 하단 **슬라이더로 투명도 조절** — 위치/투명도/기기 ID 는 `config.json` 에 저장됩니다.

## 설정 (`config.json`)

| 키 | 설명 | 기본값 |
|---|---|---|
| `backend_host` / `backend_port` | LGSTrayEx HTTP 서버 주소 | `127.0.0.1` / `12321` |
| `device_id` | 비우면 이름으로 자동 탐색 | `""` |
| `device_name_hint` | 자동 탐색용 이름 키워드 | `PRO X 2` |
| `poll_interval_seconds` | 폴링 주기 | `30` |
| `full_life_hours` | 스펙 배터리 수명(폴백) | `75` |
| `toggle_hotkey` | 표시/숨김 단축키 | `ctrl+alt+b` |
| `opacity` | 창 불투명도(0.1~1.0) | `0.85` |

## 빌드 (단일 exe)

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name "ProX2BatteryOverlay" --icon icon.ico ^
  --paths src --hidden-import keyboard --collect-submodules requests src/main.py
```

## 알려진 제약

- 일반 항상-위 오버레이는 **borderless** 전체화면 게임 위엔 표시되지만 **exclusive fullscreen** 위엔 그려지지 않습니다. FPS 등에서 쓰려면 게임을 borderless 로 두거나 보조 모니터를 사용하세요.
- LGSTrayEx 가 백그라운드에서 실행 중이어야 동작합니다. 미연결 시 오버레이에 "⚠ 백엔드 미연결" 이 표시됩니다.

## 테스트

```powershell
pip install pytest
pytest tests/
```

## 라이선스

MIT
