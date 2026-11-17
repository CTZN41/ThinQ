"""제품 종류에 의존하지 않는 모의 서비스. 네트워크/실기 전송 기능은 없습니다."""
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

from .fixtures import make_devices
from .profiles import inspect_profile, validate_value


class DeviceCatalog(Protocol):
    """PHASE 2 실기 조회 어댑터가 구현할 읽기 인터페이스."""
    def list_devices(self) -> list[dict]: ...
    def get_profile(self, device_id: str) -> dict: ...
    def get_state(self, device_id: str) -> dict: ...


@dataclass(frozen=True)
class MockIntent:
    """LG payload가 아닌 모의 명령 의도. UI와 제어 어댑터 경계용."""
    device_id: str
    capability_key: str
    value: object
    revision: int


class MockCatalog:
    def __init__(self):
        self._devices = {d["deviceId"]: d for d in make_devices()}
        self._revisions = {key: 0 for key in self._devices}

    def _get(self, device_id):
        if device_id not in self._devices:
            raise ValueError("등록된 모의 제품이 아닙니다.")
        return self._devices[device_id]

    def list_devices(self):
        return [{k: d[k] for k in ("deviceId", "name", "deviceType", "online")} for d in self._devices.values()]

    def get_profile(self, device_id):
        return deepcopy(self._get(device_id)["profile"])

    def get_state(self, device_id):
        return deepcopy(self._get(device_id)["state"])

    def inspect(self, device_id):
        device = self._get(device_id)
        capabilities, warnings = inspect_profile(self.get_profile(device_id))
        return {"mode": "MOCK", "device": {k: device[k] for k in ("deviceId", "name", "deviceType", "online")},
                "capabilities": [c.public() for c in capabilities], "warnings": warnings,
                "state": self.get_state(device_id), "revision": self._revisions[device_id]}

    def prepare(self, device_id, key, value):
        device = self._get(device_id)
        if not device["online"]:
            raise ValueError("오프라인 제품은 제어할 수 없습니다.")
        capabilities, _ = inspect_profile(self.get_profile(device_id))
        capability = next((c for c in capabilities if c.key == key), None)
        if capability is None:
            raise ValueError("프로필에 없는 제어 항목입니다.")
        validate_value(capability, value)
        return MockIntent(device_id, key, value, self._revisions[device_id])

    def simulate(self, intent: MockIntent):
        # 준비 이후에도 최신 프로필/연결 상태/값을 다시 검증합니다.
        verified = self.prepare(intent.device_id, intent.capability_key, intent.value)
        if intent.revision != verified.revision:
            raise ValueError("모의 상태가 변경되었습니다. 명령을 다시 준비하세요.")
        device = self._get(intent.device_id)
        before = deepcopy(device["state"].get(intent.capability_key))
        device["state"][intent.capability_key] = deepcopy(intent.value)
        self._revisions[intent.device_id] += 1
        return {"mode": "MOCK", "real_device_command_sent": False,
                "deviceId": intent.device_id, "key": intent.capability_key,
                "before": before, "after": intent.value,
                "note": "메모리 안의 모의 값만 변경했습니다. 실제 가전 동작/상태 전이 시뮬레이션은 아닙니다."}
