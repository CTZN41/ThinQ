"""Pinned official SDK adapters. Compile commands with an offline capture API first."""
import inspect
from copy import deepcopy

import thinqconnect as sdk

from .profiles import Capability, _constraint_error, validate_value


def device_registry():
    # Canonical matching only uses classes exported by the pinned official SDK.
    classes = {n.removesuffix("Device").replace("_", "").upper(): getattr(sdk, n)
               for n in sdk.__all__ if n.endswith("Device") and n not in ("BaseDevice", "ConnectBaseDevice")}
    types = [v for k, v in vars(sdk.DeviceType).items() if not k.startswith("_") and isinstance(v, str)]
    return {t: classes[t.removeprefix("DEVICE_").replace("_", "")]
            for t in types if t.removeprefix("DEVICE_").replace("_", "") in classes}


class CaptureAPI:
    """Intentionally cannot call a network. Only accepts a generated control payload."""
    def __init__(self):
        self.payloads = []

    async def async_post_device_control(self, device_id, payload, **kwargs):
        self.payloads.append(deepcopy(payload))
        return {}


def make_device(info, profile, api):
    cls = device_registry().get(info["deviceType"])
    if cls is None:
        raise ValueError("SDK 미지원 제품 종류: 원본 조회만 가능합니다.")
    return cls(thinq_api=api, device_id=info["deviceId"], device_type=info["deviceType"],
               model_name=info.get("modelName", ""), alias=info["name"], reportable=True, profile=profile)


def schema(node, attr):
    prop = node.profiles.get_property(attr)
    kind = prop["type"]
    values = prop.get("w")
    if kind == "boolean" and values is True:
        values = [True, False]
    if kind == "range" and isinstance(values, dict):
        values = {"step": 1, **values}
    reason = _constraint_error(kind, values)
    return {"attribute": str(attr), "kind": kind, "constraints": values,
            "unit": prop.get("unit"), "blocked_reason": reason}


def controls_for(device):
    controls = []
    nodes = [("MAIN", device)] + [(str(k), v) for k, v in device._sub_devices.items()]
    for location, node in nodes:
        writable = list(node.profiles.writable_properties)
        for attr in writable:
            fn = node.get_property_set_fn(attr)
            if not fn or not fn.startswith("set_"):
                continue
            params = list(inspect.signature(getattr(node, fn)).parameters.values())
            # Ambiguous multi-parameter mappings are not guessed.
            if len(params) != 1 or params[0].kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
                continue
            field = schema(node, attr)
            if not field["blocked_reason"]:
                controls.append({"id": f"{location}:{fn}", "label": str(attr), "location": location,
                                 "method": fn, "fields": [{**field, "name": params[0].name}]})
        # Explicit multi-attribute oven mapping. All required attributes must be writable.
        for unit in ("c", "f"):
            fn = f"set_cook_mode_with_temperature_{unit}"
            needed = ["cook_mode", f"target_temperature_{unit}", "oven_operation_mode"]
            if hasattr(node, fn) and all(a in writable for a in needed):
                fields = [{**schema(node, needed[0]), "name": "mode"},
                          {**schema(node, needed[1]), "name": "target_temperature"}]
                operation = node.profiles.get_property("oven_operation_mode").get("w", [])
                if "START" in operation and all(not f["blocked_reason"] for f in fields):
                    controls.append({"id": f"{location}:{fn}", "label": "조리 모드 + 온도 + 시작",
                                     "location": location, "method": fn, "fields": fields})
    # A custom setter may represent multiple properties; do not expose duplicate IDs.
    return list({c["id"]: c for c in controls}.values())


async def compile_control(info, profile, control_id, params):
    capture = CaptureAPI()
    device = make_device(info, profile, capture)
    control = next((c for c in controls_for(device) if c["id"] == control_id), None)
    if control is None:
        raise ValueError("지원되는 제어 명령이 아닙니다.")
    if not isinstance(params, dict) or set(params) != {f["name"] for f in control["fields"]}:
        raise ValueError("제어 매개변수가 일치하지 않습니다.")
    for field in control["fields"]:
        cap = Capability((), field["kind"], False, True, field["constraints"], ())
        validate_value(cap, params[field["name"]])
    node = device if control["location"] == "MAIN" else device._sub_devices[control["location"]]
    await getattr(node, control["method"])(**params)
    if len(capture.payloads) != 1:
        raise ValueError("단일 요청으로 변환할 수 없는 명령입니다.")
    return capture.payloads[0]
