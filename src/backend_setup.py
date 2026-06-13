"""일반 사용자용 원클릭 부트스트랩.

오버레이 앱이 의존하는 백엔드(LGSTrayEx)가 없거나 꺼져 있으면,
공식 GitHub 릴리스에서 standalone 빌드를 자동 다운로드 → 압축 해제 →
appsettings.toml 의 HTTP 서버를 켜고(127.0.0.1) → 실행한다.

LGSTrayEx 는 GPL-3.0 별도 프로젝트이므로 저장소에 동봉하지 않고
실행 시점에 사용자 PC로 내려받는다(재배포 회피).
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import zipfile

import requests

LATEST_API = "https://api.github.com/repos/strain08/LGSTrayEx/releases/latest"

# 사용자별 설치 위치 (관리자 권한 불필요)
INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "ProX2BatteryOverlay",
    "LGSTrayEx",
)
EXE_NAME = "LGSTray.exe"


def backend_exe_path() -> str:
    return os.path.join(INSTALL_DIR, EXE_NAME)


def is_installed() -> bool:
    return os.path.isfile(backend_exe_path())


def is_backend_running(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        requests.get(f"http://{host}:{port}/", timeout=timeout)
        return True
    except requests.RequestException:
        return False


def is_process_running() -> bool:
    """LGSTray.exe 프로세스가 떠 있는지 (tasklist 사용)."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/NH"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        return EXE_NAME.lower() in out.lower()
    except Exception:
        return False


def _find_standalone_asset() -> tuple[str, int]:
    """최신 릴리스에서 standalone zip 의 (download_url, size) 반환."""
    r = requests.get(LATEST_API, timeout=20)
    r.raise_for_status()
    assets = r.json().get("assets", [])
    for a in assets:
        name = a.get("name", "").lower()
        if "standalone" in name and name.endswith(".zip"):
            return a["browser_download_url"], a.get("size", 0)
    # 폴백: 첫 zip
    for a in assets:
        if a.get("name", "").lower().endswith(".zip"):
            return a["browser_download_url"], a.get("size", 0)
    raise RuntimeError("LGSTrayEx 릴리스에서 다운로드할 zip 을 찾지 못했습니다.")


def download_and_install(progress_cb=None) -> None:
    """standalone zip 다운로드 → INSTALL_DIR 에 압축 해제 → toml 패치.

    progress_cb(percent:int, message:str) 로 진행률 보고(없으면 무시).
    """
    def report(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    os.makedirs(INSTALL_DIR, exist_ok=True)
    url, size = _find_standalone_asset()
    zip_path = os.path.join(INSTALL_DIR, "_download.zip")

    report(0, "백엔드(LGSTrayEx) 내려받는 중…")
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", size) or 0)
        done = 0
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if total:
                    report(int(done * 90 / total),
                           f"백엔드 내려받는 중… {done >> 20}/{total >> 20} MB")

    report(92, "압축 푸는 중…")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(INSTALL_DIR)
    try:
        os.remove(zip_path)
    except OSError:
        pass

    # 일부 zip 은 하위 폴더에 풀릴 수 있으니 exe 위치 보정
    _flatten_if_nested()

    report(96, "설정 적용 중…")
    toml = os.path.join(INSTALL_DIR, "appsettings.toml")
    if os.path.isfile(toml):
        patch_http_server(toml)
    report(100, "설치 완료")


def _flatten_if_nested() -> None:
    """exe 가 INSTALL_DIR 하위 폴더에 있으면 그 폴더를 기준으로 쓰도록 보정."""
    global INSTALL_DIR
    if is_installed():
        return
    for root, _dirs, files in os.walk(INSTALL_DIR):
        if EXE_NAME in files:
            # exe 가 들어있는 폴더를 INSTALL_DIR 로 간주하도록 전역 갱신
            INSTALL_DIR = root
            return


def patch_http_server(toml_path: str, host: str = "127.0.0.1",
                      port: int = 12321) -> None:
    """[HTTPServer] 섹션만 골라 enabled/addr/port/useIpv6 를 설정한다."""
    with open(toml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    in_http = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_http = stripped.lower() == "[httpserver]"
            out.append(line)
            continue
        if in_http:
            if re.match(r"\s*enabled\s*=", line):
                out.append("enabled = true\n"); continue
            if re.match(r"\s*addr\s*=", line):
                out.append(f'addr = "{host}"\n'); continue
            if re.match(r"\s*port\s*=", line):
                out.append(f"port = {port}\n"); continue
            if re.match(r"\s*useIpv6\s*=", line):
                out.append("useIpv6 = false\n"); continue
        out.append(line)

    with open(toml_path, "w", encoding="utf-8") as f:
        f.writelines(out)


def kill_backend() -> None:
    """실행 중인 LGSTray / LGSTrayHID 종료 (toml 재적용 후 재시작용)."""
    for name in ("LGSTray.exe", "LGSTrayHID.exe"):
        try:
            subprocess.run(["taskkill", "/F", "/IM", name],
                           capture_output=True, timeout=10)
        except Exception:
            pass
    time.sleep(1.0)


def installed_toml_path() -> str:
    return os.path.join(INSTALL_DIR, "appsettings.toml")


def launch_backend() -> None:
    exe = backend_exe_path()
    if not os.path.isfile(exe):
        raise RuntimeError("LGSTray.exe 를 찾을 수 없습니다.")
    # 콘솔창 없이 독립 실행
    creationflags = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
    subprocess.Popen([exe], cwd=INSTALL_DIR, creationflags=creationflags,
                     close_fds=True)


def wait_until_up(host: str, port: int, timeout_s: float = 40.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if is_backend_running(host, port):
            return True
        time.sleep(1.0)
    return False


def ensure_backend(host: str, port: int, progress_cb=None) -> bool:
    """백엔드가 응답하도록 보장. 반환값: 최종 가용 여부."""
    def report(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    # 이미 HTTP 가 응답하면 끝.
    if is_backend_running(host, port):
        return True

    if not is_installed():
        download_and_install(progress_cb)
    else:
        # 설치돼 있어도 exe 위치(중첩 폴더)를 잡아둔다.
        _flatten_if_nested()

    # 설치 여부와 무관하게 HTTP 서버 설정을 항상 보정한다.
    # (이전 설치본이 HTTP 꺼진 상태로 남아 있을 수 있음)
    toml = installed_toml_path()
    if os.path.isfile(toml):
        patch_http_server(toml, host, port)

    # HTTP 가 꺼진 채 떠 있을 수 있으니, 응답 없으면 (재)시작한다.
    report(100, "백엔드 시작 중…")
    if is_process_running():
        kill_backend()
    launch_backend()

    report(100, "마우스 연결 대기 중…")
    return wait_until_up(host, port)
