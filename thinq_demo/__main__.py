"""python -m thinq_demo : VS Code 터미널용 PHASE 1 시연."""
import argparse
import json
import sys
from dataclasses import asdict

from .service import MockCatalog


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def run_demo():
    catalog = MockCatalog()
    print("=== ThinQ PHASE 1 | MOCK ONLY | 실기 명령 전송 없음 ===")
    for device in catalog.list_devices():
        detail = catalog.inspect(device["deviceId"])
        count = sum(c["actionable"] for c in detail["capabilities"])
        state = "온라인" if device["online"] else "오프라인"
        print(f"{device['deviceId']:14} {device['name']:12} | {state} | 해석된 쓰기 항목 {count}")
    print("\n[정상 시나리오] 에어컨 모의 목표 온도 25 → 24.5")
    intent = catalog.prepare("mock-ac", "/property/temperature/targetTemperature", 24.5)
    emit(catalog.simulate(intent))
    print("\n[차단 시나리오]")
    for device_id, key, value in [
        ("mock-ac", "/property/temperature/targetTemperature", 99),
        ("mock-air", "/property/sensor/pm25", 0),
        ("mock-offline", "/property/operation/mode", "ON"),
        ("mock-unknown", "/property/custom/schedule", {}),
    ]:
        try:
            catalog.prepare(device_id, key, value)
        except ValueError as exc:
            print(f"차단됨 | {device_id} | {exc}")
        else:
            raise AssertionError("차단되어야 하는 명령이 허용되었습니다.")
    print("\n시연 완료. 실행을 종료하면 모의 변경 사항은 초기화됩니다.")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="ThinQ PHASE 1: 인증정보·네트워크 없이 모의 제품 검증")
    subs = parser.add_subparsers(dest="command")
    subs.add_parser("demo", help="전체 모의 시연 (기본)")
    subs.add_parser("list", help="모의 제품 목록")
    detail = subs.add_parser("inspect", help="제품 프로필·지원 항목·현재 모의 값")
    detail.add_argument("device_id")
    detail.add_argument("--raw", action="store_true", help="원본 합성 프로필 보기")
    prepare = subs.add_parser("prepare", help="명령 검증/미리보기. 값 변경 없음")
    prepare.add_argument("device_id")
    prepare.add_argument("key")
    prepare.add_argument("value", help='JSON 값: 24.5 / true / 문자열은 JSON 따옴표 필요')
    args = parser.parse_args(argv)
    catalog = MockCatalog()
    try:
        if args.command in (None, "demo"):
            run_demo()
        elif args.command == "list":
            emit({"mode": "MOCK", "devices": catalog.list_devices()})
        elif args.command == "inspect":
            emit(catalog.get_profile(args.device_id) if args.raw else catalog.inspect(args.device_id))
        elif args.command == "prepare":
            intent = catalog.prepare(args.device_id, args.key, json.loads(args.value))
            emit({"mode": "MOCK", "real_device_command_sent": False, "intent": asdict(intent)})
    except (ValueError, TypeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
