"""Loopback-only local web demo. Explicit mode; same-origin and CSRF checks."""
import argparse
import json
import secrets
from pathlib import Path

from aiohttp import web

from .config import live_settings
from .engine import Engine
from .live import LiveGateway, safe_error
from . import ai

STATIC = Path(__file__).with_name("static")
ENGINE = web.AppKey("engine", Engine)
CSRF = web.AppKey("csrf", str)
HOSTS = web.AppKey("allowed_hosts", set)


@web.middleware
async def protect(request, handler):
    if request.host not in request.app[HOSTS]:
        return web.json_response({"error": "로컬 주소로 접속하세요."}, status=403)
    origin = request.headers.get("Origin")
    if origin and origin != f"http://{request.host}":
        return web.json_response({"error": "다른 출처의 요청은 허용하지 않습니다."}, status=403)
    if request.method == "POST":
        if not secrets.compare_digest(request.headers.get("X-Demo-CSRF", ""), request.app[CSRF]):
            return web.json_response({"error": "요청 확인값이 없습니다. 화면을 새로고침하세요."}, status=403)
    try:
        response = await handler(request)
    except web.HTTPException:
        raise
    except (ValueError, KeyError, TypeError):
        response = web.json_response({"error": "요청을 처리할 수 없습니다. 제품·값·미리보기 유효기간과 최신 상태를 확인하세요."}, status=400)
    except Exception as exc:
        response = web.json_response({"error": safe_error(exc)}, status=502)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response


async def body(request):
    data = await request.json(loads=lambda s: json.loads(s, parse_constant=lambda v: (_ for _ in ()).throw(ValueError("nonfinite"))))
    if not isinstance(data, dict):
        raise ValueError("JSON 객체 필요")
    return data


async def config(request):
    return web.json_response({"mode": request.app[ENGINE].mode, "country": "KR", "country_label": "대한민국 (+82)",
                              "csrf": request.app[CSRF], "sdk_version": "1.0.14", "live_verified": False})


async def devices(request):
    return web.json_response({"devices": await request.app[ENGINE].devices()})


async def detail(request):
    return web.json_response(await request.app[ENGINE].detail(request.match_info["device_id"]))


async def prepare(request):
    data = await body(request)
    return web.json_response(await request.app[ENGINE].prepare(data["device_id"], data["control_id"], data["params"]))


async def confirm(request):
    data = await body(request)
    if not isinstance(data.get("ticket"), str):
        raise ValueError("ticket 필요")
    return web.json_response(await request.app[ENGINE].confirm(data["ticket"]))


async def apply(request):
    data = await body(request)
    return web.json_response(await request.app[ENGINE].apply(data["device_id"], data["changes"]))


async def ai_status(request):
    key, model = ai.settings()
    return web.json_response({'configured': bool(key), 'model': model,
                              'enabled': request.app[ENGINE].mode == 'MOCK'})


async def ai_apply(request):
    data = await body(request)
    try:
        return web.json_response(await ai.execute(request.app[ENGINE], data.get('device_id'), data.get('prompt')))
    except (ValueError, KeyError, TypeError) as exc:
        # Only locally constructed ValueErrors are exposed; never provider response bodies.
        message = str(exc) if isinstance(exc, ValueError) else 'AI 설정 형식이 올바르지 않습니다.'
        return web.json_response({'error': message}, status=400)


async def asset(request):
    name = request.match_info.get("asset", "index.html")
    if name not in {"index.html", "app.js", "style.css"}:
        raise web.HTTPNotFound()
    return web.FileResponse(STATIC / name)


def create_app(engine=None, port=8765):
    app = web.Application(middlewares=[protect], client_max_size=16384)
    app[ENGINE] = engine or Engine()
    app[CSRF] = secrets.token_urlsafe(32)
    app[HOSTS] = {f"127.0.0.1:{port}", f"localhost:{port}"}
    app.router.add_get("/api/config", config)
    app.router.add_get("/api/devices", devices)
    app.router.add_get("/api/devices/{device_id}", detail)
    app.router.add_post("/api/prepare", prepare)
    app.router.add_post("/api/confirm", confirm)
    app.router.add_post("/api/apply", apply)
    app.router.add_get("/api/ai/status", ai_status)
    app.router.add_post("/api/ai/apply", ai_apply)
    app.router.add_get("/", asset)
    app.router.add_get("/{asset}", asset)
    if app[ENGINE].gateway:
        async def lifecycle(app):
            await app[ENGINE].gateway.start()
            try:
                yield
            finally:
                await app[ENGINE].gateway.close()
        app.cleanup_ctx.append(lifecycle)
    return app


def main():
    parser = argparse.ArgumentParser(description="ThinQ local demo")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    gateway = None
    if args.mode == "live":
        try:
            gateway = LiveGateway(*live_settings())
        except ValueError as exc:
            parser.exit(2, str(exc) + "\n")
    print(f"ThinQ {args.mode.upper()} | KR | http://127.0.0.1:{args.port}", flush=True)
    web.run_app(create_app(Engine(gateway), args.port), host="127.0.0.1", port=args.port, access_log=None, print=None)


if __name__ == "__main__":
    main()
