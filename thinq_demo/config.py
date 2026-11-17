"""Local configuration. Mock mode never loads a PAT, even from the environment."""
import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def country_code(value):
    value = value.strip().upper()
    if value in ("KR", "+82", "82", "대한민국"):
        return "KR"
    raise ValueError("이 데모의 국가 코드는 대한민국(KR)입니다.")


def live_settings(root=ROOT):
    values = {}
    path = root / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    pat = os.environ.get("THINQ_PAT", values.get("THINQ_PAT", "")).strip()
    country = country_code(os.environ.get("THINQ_COUNTRY", values.get("THINQ_COUNTRY", "KR")))
    if not pat:
        raise ValueError("PAT가 없습니다. 모의 모드를 사용하거나 로컬 .env에 설정한 후 다시 실행하세요.")
    private = root / "private"
    private.mkdir(exist_ok=True)
    client_file = private / "client_id.txt"
    if client_file.exists():
        client_id = str(uuid.UUID(client_file.read_text().strip()))
    else:
        client_id = str(uuid.uuid4())
        client_file.write_text(client_id, encoding="utf-8")
    return pat, country, client_id
