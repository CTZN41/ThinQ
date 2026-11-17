"""Real API transport; created only by explicit --mode live with a nonempty PAT."""
import asyncio
import logging

from aiohttp import ClientSession, ClientTimeout
from thinqconnect import ThinQApi


class LiveGateway:
    def __init__(self, pat, country, client_id):
        self._credentials = (pat, country, client_id)
        self.session = None
        self.api = None

    async def start(self):
        # SDK exception strings and debug logs can contain response data. Never expose them to UI.
        logging.getLogger("thinqconnect").disabled = True
        self.session = ClientSession(timeout=ClientTimeout(total=20))
        self.api = ThinQApi(self.session, *self._credentials)

    async def close(self):
        if self.session:
            await self.session.close()

    async def list_devices(self):
        rows = await self.api.async_get_device_list()
        if not isinstance(rows, list):
            raise ValueError("제품 목록 응답 형식을 확인할 수 없습니다.")
        result = []
        for row in rows:
            info = row.get("deviceInfo") or {}
            if row.get("deviceId"):
                result.append({"deviceId": row["deviceId"], "name": info.get("alias") or "이름 없는 제품",
                               "deviceType": info.get("deviceType", "UNKNOWN"),
                               "modelName": info.get("modelName", ""), "online": None})
        return result

    async def snapshot(self, device_id):
        profile, state = await asyncio.gather(self.api.async_get_device_profile(device_id),
                                              self.api.async_get_device_status(device_id))
        if not isinstance(profile, dict) or not isinstance(state, (dict, list)):
            raise ValueError("프로필 또는 상태 응답 형식을 확인할 수 없습니다.")
        return profile, state

    async def control(self, device_id, payload):
        # No automatic retry: network timeout can mean a command was already accepted.
        return await self.api.async_post_device_control(device_id, payload)


def safe_error(exc):
    code = str(getattr(exc, "code", ""))
    if code in ("1103", "1218", "1302"):
        return "인증 실패: 로컬 PAT 설정을 확인하세요."
    if code == "1306":
        return "API 호출 제한: 잠시 후 수동으로 다시 조회하세요."
    if code in ("1219", "1220", "1221", "2101", "2201", "2202"):
        return "해당 제품 또는 기능이 API에서 지원되지 않습니다."
    if code in ("1222", "2301", "2302", "2303", "2304", "2305"):
        return "현재 제품 상태에서는 요청할 수 없습니다. 연결·원격 제어 설정을 확인하세요."
    if code == "1308":
        return "해당 제품의 제어 권한이 없습니다."
    # Deliberately omit upstream message/header/token/body.
    return "ThinQ 요청을 완료하지 못했습니다. 인증·네트워크·제품 상태를 확인하세요."
