"""합성 프로필: LG 실기 응답이 아니며 특정 모델 지원을 증명하지 않습니다."""
from copy import deepcopy


def enum(values, *, writable=True):
    modes = ["r", "w"] if writable else ["r"]
    return {"type": "enum", "mode": modes, "value": {m: values for m in modes}}


def number_range(low, high, step=1):
    return {"type": "range", "mode": ["r", "w"],
            "value": {m: {"min": low, "max": high, "step": step} for m in ("r", "w")}}


def boolean():
    return {"type": "boolean", "mode": ["r", "w"], "value": {"w": [True, False]}}


def sample(device_id, name, device_type, properties, values, *, online=True):
    # values는 프로필 JSON pointer -> 모의 현재 값. 실제 API state 스키마와 다릅니다.
    return {"deviceId": device_id, "name": name, "deviceType": device_type,
            "online": online, "profile": {"property": properties}, "state": values}


def make_devices():
    return deepcopy([
        sample("mock-ac", "거실 에어컨", "DEVICE_AIR_CONDITIONER", {
            "operation": {"airConOperationMode": enum(["POWER_ON", "POWER_OFF"])},
            "temperature": {"unit": "C", "targetTemperature": number_range(18, 30, 0.5)},
        }, {"/property/operation/airConOperationMode": "POWER_OFF",
            "/property/temperature/targetTemperature": 25}),
        sample("mock-air", "공기청정기", "DEVICE_AIR_PURIFIER", {
            "operation": {"mode": enum(["ON", "OFF"])},
            "sensor": {"pm25": {"type": "number", "mode": ["r"]}},
        }, {"/property/operation/mode": "OFF", "/property/sensor/pm25": 12}),
        sample("mock-washer", "세탁기", "DEVICE_WASHER", {
            "operation": {"command": enum(["PAUSE", "STOP"])},
            "runState": {"currentState": enum(["RUNNING", "PAUSED", "DONE"], writable=False)},
        }, {"/property/operation/command": "PAUSE", "/property/runState/currentState": "RUNNING"}),
        sample("mock-fridge", "냉장고", "DEVICE_REFRIGERATOR", {
            "temperature": {"unit": "C", "targetTemperature": number_range(1, 7)},
            "express": {"enabled": boolean()},
        }, {"/property/temperature/targetTemperature": 3, "/property/express/enabled": False}),
        sample("mock-oven", "상·하단 오븐", "DEVICE_OVEN", [
            {"location": {"locationName": location},
             "temperature": [{"unit": "C", "targetTemperature": number_range(80, 230, 5)}],
             "operation": {"command": enum(["STOP"])}}
            for location in ("UPPER", "LOWER")
        ], {f"/property/{i}/temperature/0/targetTemperature": 180 for i in (0, 1)}),
        sample("mock-offline", "연결 끊긴 청정기", "DEVICE_AIR_PURIFIER", {
            "operation": {"mode": enum(["ON", "OFF"])}
        }, {"/property/operation/mode": "OFF"}, online=False),
        sample("mock-unknown", "미지원 형식 제품", "DEVICE_FUTURE", {
            "custom": {"schedule": {"type": "vendorObject", "mode": ["r", "w"]}},
        }, {"/property/custom/schedule": {"vendor": "sample"}}),
    ])
