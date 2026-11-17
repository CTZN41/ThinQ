import asyncio
import hashlib
import json
import secrets
import time

from .live import safe_error
from .profiles import inspect_profile
from .sdk_adapter import CaptureAPI, compile_control, controls_for, make_device
from .service import MockCatalog


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class Engine:
    def __init__(self, gateway=None):
        self.gateway = gateway
        self.mode = "LIVE" if gateway else "MOCK"
        self.mock = MockCatalog()
        self.pending = {}
        self.lock = asyncio.Lock()

    async def devices(self):
        return await self.gateway.list_devices() if self.gateway else self.mock.list_devices()

    async def detail(self, device_id):
        devices = await self.devices()
        info = next((d for d in devices if d["deviceId"] == device_id), None)
        if info is None:
            raise ValueError("제품 목록에 없는 ID입니다.")
        if not self.gateway:
            detail = self.mock.inspect(device_id)
            profile = self.mock.get_profile(device_id)
            detail["controls"] = [
                {"id": c["key"], "label": c["key"].split("/")[-1],
                 "location": " / ".join(str(x.get("location", {}).get("locationName", "")) for x in c["context"]).strip(" / ") or "MAIN",
                 "fields": [{"name": "value", "kind": c["kind"], "constraints": c["constraints"], "current": detail["state"].get(c["key"]), "unit": next((x["unit"] for x in c["context"] if "unit" in x), None)}]}
                for c in detail["capabilities"] if c["actionable"]]
            detail["raw_profile"] = profile
            return detail
        profile, state = await self.gateway.snapshot(device_id)
        caps, warnings = inspect_profile(profile)
        try:
            device = make_device(info, profile, CaptureAPI())
            controls = controls_for(device)
        except Exception:
            controls = []
            warnings.append("SDK가 이 프로필을 해석하지 못했습니다. 원본 조회만 제공합니다.")
        return {"mode": self.mode, "device": info, "capabilities": [c.public() for c in caps],
                "controls": controls, "warnings": warnings,
                "raw_profile": profile, "state": state}

    async def prepare(self, device_id, control_id, params):
        detail = await self.detail(device_id)
        if not any(c["id"] == control_id for c in detail["controls"]):
            raise ValueError("해당 제품의 지원 명령이 아닙니다.")
        if self.gateway:
            payload = await compile_control(detail["device"], detail["raw_profile"], control_id, params)
        else:
            if not isinstance(params, dict) or set(params) != {"value"}:
                raise ValueError("value 값 하나가 필요합니다.")
            self.mock.prepare(device_id, control_id, params["value"])
            payload = {"mock_property": control_id, "value": params["value"]}
        # Prune expired previews; memory remains bounded for a long-running local demo.
        now = time.monotonic()
        self.pending = {k: v for k, v in self.pending.items() if v["expires"] > now}
        if len(self.pending) >= 100:
            raise ValueError("열린 미리보기가 너무 많습니다. 2분 후 다시 시도하세요.")
        ticket = secrets.token_urlsafe(24)
        self.pending[ticket] = {"device_id": device_id, "control_id": control_id, "params": params,
                                "snapshot": digest([detail["raw_profile"], detail["state"]]),
                                "payload": payload, "expires": now + 120}
        return {"ticket": ticket, "mode": self.mode, "device": detail["device"], "payload": payload,
                "control_id": control_id, "expires_in": 120,
                "message": "모의 값만 변경됩니다." if not self.gateway else "아래 요청이 실제 제품으로 전송됩니다. 시작 명령 포함 여부도 확인하세요."}

    async def apply(self, device_id, changes):
        """Validate the complete selection before sending; stop on uncertain delivery."""
        if not isinstance(changes, list) or not 1 <= len(changes) <= 50:
            raise ValueError("변경 항목이 필요합니다.")
        async with self.lock:
            detail = await self.detail(device_id)
            supported = {c["id"] for c in detail["controls"]}
            seen, compiled = set(), []
            for change in changes:
                cid, params = change["control_id"], change["params"]
                if cid not in supported or cid in seen:
                    raise ValueError("지원하지 않거나 중복된 항목입니다.")
                seen.add(cid)
                if self.gateway:
                    payload = await compile_control(detail["device"], detail["raw_profile"], cid, params)
                else:
                    if not isinstance(params, dict) or set(params) != {"value"}:
                        raise ValueError("value 값 하나가 필요합니다.")
                    payload = self.mock.prepare(device_id, cid, params["value"])
                compiled.append((cid, payload))
            results = []
            for cid, payload in compiled:
                try:
                    if self.gateway:
                        await self.gateway.control(device_id, payload)
                        result = {"status": "ACCEPTED"}
                    else:
                        fresh = self.mock.prepare(device_id, cid, payload.value)
                        result = self.mock.simulate(fresh)
                    results.append({"control_id": cid, "result": result})
                except Exception:
                    results.append({"control_id": cid, "result": {"status": "UNKNOWN"}})
                    break
            return {"mode": self.mode, "results": results,
                    "remaining": len(compiled) - len(results),
                    "note": "선택한 설정을 순서대로 전송했습니다. 일부 실패 시 이전 설정은 되돌리지 않으며 자동 재전송하지 않습니다. 실제 작동은 제품 상태로 확인하세요."}

    async def confirm(self, ticket):
        async with self.lock:
            command = self.pending.pop(ticket, None)
            if not command or command["expires"] <= time.monotonic():
                raise ValueError("미리보기가 만료되었거나 이미 사용되었습니다. 다시 준비하세요.")
            detail = await self.detail(command["device_id"])
            if digest([detail["raw_profile"], detail["state"]]) != command["snapshot"]:
                raise ValueError("제품 상태 또는 프로필이 바뀌었습니다. 새 미리보기를 확인하세요.")
            if not self.gateway:
                intent = self.mock.prepare(command["device_id"], command["control_id"], command["params"]["value"])
                return self.mock.simulate(intent)
            payload = await compile_control(detail["device"], detail["raw_profile"], command["control_id"], command["params"])
            if payload != command["payload"]:
                raise ValueError("요청 내용이 변경되었습니다. 다시 준비하세요.")
            try:
                await self.gateway.control(command["device_id"], payload)
            except Exception as exc:
                return {"mode": "LIVE", "status": "UNKNOWN", "message": safe_error(exc),
                        "note": "전송 결과 미확정. 자동 재전송하지 않습니다. 제품 상태를 직접 확인하세요."}
            try:
                _, state = await self.gateway.snapshot(command["device_id"])
                return {"mode": "LIVE", "status": "ACCEPTED", "observed_state": state,
                        "note": "API 요청 접수 후 상태를 재조회했습니다. 물리 작동 성공을 자동 판정하지 않습니다."}
            except Exception:
                return {"mode": "LIVE", "status": "ACCEPTED_STATE_UNKNOWN",
                        "note": "요청은 접수됐으나 상태 재조회 실패. 자동 재전송하지 않습니다."}
