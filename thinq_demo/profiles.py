"""Conservative profile inspection, not a universal ThinQ command compiler.

Paths keep array indices and location/unit context. An actionable field can be
used in a mock intent; a future device adapter must construct the live payload.
"""
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class Capability:
    path: tuple[str | int, ...]
    kind: str
    readable: bool
    writable: bool
    constraints: Any
    context: tuple[dict, ...]
    blocked_reason: str | None = None

    @property
    def key(self) -> str:
        # RFC 6901 JSON pointer avoids ambiguous paths and array locations.
        return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in self.path)

    @property
    def actionable(self) -> bool:
        return self.writable and self.blocked_reason is None

    def public(self) -> dict:
        return {**asdict(self), "key": self.key, "actionable": self.actionable}


def _number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and isfinite(value)
    except OverflowError:
        return False


def _constraint_error(kind: str, values: Any) -> str | None:
    if kind == "enum":
        if not isinstance(values, list) or not values or any(type(v) not in (str, int, float, bool) for v in values):
            return "허용 선택값 정보 부족"
        if any(type(v) is float and not isfinite(v) for v in values):
            return "유효하지 않은 선택값"
        return None
    if kind == "range":
        if not isinstance(values, dict) or not all(_number(values.get(k)) for k in ("min", "max", "step")):
            return "수치 범위·간격 정보 부족"
        if values["min"] > values["max"] or values["step"] <= 0:
            return "유효하지 않은 수치 범위"
        if "except" in values and (not isinstance(values["except"], list) or not all(_number(v) for v in values["except"])):
            return "유효하지 않은 제외값"
        return None
    if kind == "boolean":
        if not isinstance(values, list) or not values or any(type(v) is not bool for v in values):
            return "허용 boolean 값 정보 부족"
        return None
    return "지원하지 않는 속성 형식: 조회만 가능"


def inspect_profile(profile: dict) -> tuple[list[Capability], list[str]]:
    """Read mode/value.w only; never infer write permission from a property name."""
    capabilities: list[Capability] = []
    warnings: list[str] = []

    def walk(node: Any, path: tuple, context: tuple) -> None:
        if isinstance(node, list):
            for i, child in enumerate(node):
                walk(child, path + (i,), context)
            return
        if not isinstance(node, dict):
            return
        local = {k: node[k] for k in ("location", "unit") if k in node}
        if local:
            context = context + ({"path": list(path), **local},)
        if "type" in node and ("mode" in node or "value" in node):
            modes = node.get("mode", [])
            modes = modes if isinstance(modes, list) else []
            kind = node.get("type")
            values = node.get("value", {})
            values = values.get("w") if isinstance(values, dict) else None
            writable = "w" in modes
            reason = _constraint_error(kind, values) if writable else "읽기 전용 또는 쓰기 권한 없음"
            capabilities.append(Capability(path, str(kind), "r" in modes, writable, values, context, reason))
            return
        for key, child in node.items():
            if key not in ("location", "unit"):
                walk(child, path + (key,), context)

    if not isinstance(profile, dict):
        return [], ["프로필이 객체 형식이 아닙니다."]
    for root in ("property", "extensionProperty"):
        if root in profile:
            walk(profile[root], (root,), ())
    if not capabilities:
        warnings.append("해석 가능한 속성 없음. 원본 프로필을 확인하고 어댑터를 추가하세요.")
    if any(c.writable and not c.actionable for c in capabilities):
        warnings.append("일부 쓰기 속성은 형식/제약 정보 부족으로 제어에서 제외되었습니다.")
    return capabilities, warnings


def validate_value(capability: Capability, value: Any) -> None:
    if not capability.actionable:
        raise ValueError(capability.blocked_reason or "제어 불가")
    if capability.kind in ("enum", "boolean"):
        if not any(type(value) is type(v) and value == v for v in capability.constraints):
            raise ValueError("허용된 선택값과 자료형이 아닙니다.")
    elif capability.kind == "range":
        if not _number(value):
            raise ValueError("유한한 숫자를 입력하세요. boolean은 숫자로 취급하지 않습니다.")
        try:
            number = Decimal(str(value))
            lower = Decimal(str(capability.constraints["min"]))
            upper = Decimal(str(capability.constraints["max"]))
            step = Decimal(str(capability.constraints["step"]))
            if not lower <= number <= upper or (number - lower) % step != 0:
                raise ValueError("허용 범위 또는 간격을 벗어났습니다.")
            if value in capability.constraints.get("except", []):
                raise ValueError("제품이 허용하지 않는 제외값입니다.")
        except InvalidOperation as exc:
            raise ValueError("수치 검증 실패") from exc
