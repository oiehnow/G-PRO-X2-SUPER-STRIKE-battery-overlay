"""LGSTrayEx 의 로컬 HTTP/XML 엔드포인트를 폴링해 배터리 상태를 읽는다.

엔드포인트 (LGSTrayEx / LGSTrayBattery 계열):
  GET http://{host}:{port}/            -> 디바이스 목록 XML
  GET http://{host}:{port}/device/{id} -> 해당 기기 상세 XML (이름, 배터리%, is_online)

포트/주소는 LGSTrayEx 의 appsettings.toml [HTTPServer] 설정값과 맞춰야 한다.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests


@dataclass
class BatteryStatus:
    device_id: str
    name: str
    percent: float
    is_online: bool


class BackendError(Exception):
    """백엔드(LGSTrayEx) 미실행 또는 응답 이상."""


def _text(elem: ET.Element, *tags: str) -> str | None:
    """주어진 태그 후보들 중 첫 번째로 발견되는 텍스트를 반환(대소문자 무시)."""
    wanted = {t.lower() for t in tags}
    for child in elem.iter():
        if child.tag.lower() in wanted and child.text is not None:
            return child.text.strip()
    # 속성으로 들어있는 경우도 처리
    for key, val in elem.attrib.items():
        if key.lower() in wanted:
            return val.strip()
    return None


class BackendClient:
    def __init__(self, host: str, port: int, timeout: float = 3.0):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def _get_text(self, path: str) -> str:
        url = f"{self.base}{path}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise BackendError(f"LGSTrayEx 연결 실패: {url} ({e})") from e
        return resp.text

    def _get_xml(self, path: str) -> ET.Element:
        text = self._get_text(path)
        try:
            return ET.fromstring(text)
        except ET.ParseError as e:
            raise BackendError(f"XML 파싱 실패: {self.base}{path} ({e})") from e

    def list_devices(self) -> list[tuple[str, str]]:
        """(device_id, name) 목록.

        LGSTrayEx 의 루트('/') 응답은 XML 이 아니라 HTML 링크 목록이다:
          PRO X2 SUPERSTRIKE : <a href="/device/NATIVE.Mouse.XXXX">NATIVE.Mouse.XXXX</a>
        'By Device ID' 섹션에서 (이름, deviceID) 쌍을 정규식으로 추출한다.
        """
        html = self._get_text("/")
        # "이름 : <a href="/device/ID">..." 패턴
        pairs = re.findall(
            r'([^<>:]+?)\s*:\s*<a href="/device/([^"]+)"', html
        )
        devices: list[tuple[str, str]] = []
        seen = set()
        for name, dev_id in pairs:
            dev_id = dev_id.strip()
            if dev_id and dev_id not in seen:
                seen.add(dev_id)
                devices.append((dev_id, name.strip()))
        if not devices:
            # 폴백: 모든 /device/ 링크라도 수집
            for dev_id in re.findall(r'href="/device/([^"]+)"', html):
                if dev_id not in seen:
                    seen.add(dev_id)
                    devices.append((dev_id, ""))
        return devices

    def get_all_statuses(self) -> list[BatteryStatus]:
        """감지된 모든 기기의 배터리 상태. 개별 조회 실패는 건너뛴다.

        브랜드/종류(마우스·키보드·헤드셋)와 무관하게 LGSTrayEx 가 인식한
        모든 기기를 반환한다. 필터링하지 않는다.
        """
        statuses: list[BatteryStatus] = []
        for dev_id, _name in self.list_devices():
            try:
                statuses.append(self.get_status(dev_id))
            except BackendError:
                continue  # 일부 기기 조회 실패해도 나머지는 표시
        return statuses

    def get_status(self, device_id: str) -> BatteryStatus:
        root = self._get_xml(f"/device/{device_id}")
        pct_raw = _text(root, "battery_percent", "battery_percentage",
                        "batterypercentage", "percentage")
        if pct_raw is None:
            raise BackendError("XML 에서 배터리 값을 찾지 못했습니다.")
        try:
            percent = float(pct_raw)
        except ValueError:
            raise BackendError(f"배터리 값 파싱 실패: {pct_raw!r}")
        online_raw = (_text(root, "is_online", "isonline", "online") or "").lower()
        is_online = online_raw in ("1", "true", "yes", "online")
        name = _text(root, "device_name", "name", "devicename") or device_id
        return BatteryStatus(device_id, name, percent, is_online)
