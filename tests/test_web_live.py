import asyncio
import os
import tempfile
import time
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from aiohttp.test_utils import TestClient, TestServer

from thinq_demo.config import country_code, live_settings
from thinq_demo.engine import Engine
from thinq_demo.fixtures import enum, number_range
from thinq_demo.live import safe_error
from thinq_demo.sdk_adapter import CaptureAPI, compile_control, controls_for, device_registry, make_device
from thinq_demo.web import HOSTS, create_app


INFO = {"deviceId": "test-ac", "name": "Test AC", "deviceType": "DEVICE_AIR_CONDITIONER"}
PROFILE = {"property": {"operation": {"airConOperationMode": enum(["POWER_ON", "POWER_OFF"])}}}
OVEN_INFO = {"deviceId": "test-oven", "name": "Test oven", "deviceType": "DEVICE_OVEN"}
OVEN_PROFILE = {"extensionProperty": {"info": {"type": "SINGLE"}}, "property": [
    {"location": {"locationName": "OVEN"}, "operation": {"ovenOperationMode": enum(["START", "STOP"])},
     "cook": {"cookMode": enum(["BAKE", "CONVECTION"])},
     "temperature": [{"unit": "C", "targetTemperature": number_range(80, 230, 5)}]}
]}


class FakeGateway:
    def __init__(self):
        self.calls = 0
        self.state = {"operation": {"airConOperationMode": "POWER_OFF"}}
        self.profile = deepcopy(PROFILE)
        self.fail_control = False

    async def list_devices(self):
        return [deepcopy(INFO)]

    async def snapshot(self, device_id):
        return deepcopy(self.profile), deepcopy(self.state)

    async def control(self, device_id, payload):
        self.calls += 1
        if self.fail_control:
            raise TimeoutError("do-not-expose-secret")
        self.state = deepcopy(payload)
        return {}


class SDKTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_power_on_before_mode(self):
        gateway = FakeGateway()
        gateway.profile['property']['airConJobMode'] = {'currentJobMode': enum(['FAN', 'AIR_DRY'])}
        sent = []
        async def record(device_id, payload):
            sent.append(payload)
        gateway.control = record
        await Engine(gateway).apply('test-ac', [
            {'control_id':'MAIN:set_current_job_mode','params':{'mode':'AIR_DRY'}},
            {'control_id':'MAIN:set_air_con_operation_mode','params':{'operation':'POWER_ON'}}])
        self.assertEqual(sent[0]['operation']['airConOperationMode'], 'POWER_ON')
        self.assertEqual(sent[1]['airConJobMode']['currentJobMode'], 'AIR_DRY')

    async def test_error_details_without_secret(self):
        gateway = FakeGateway()
        async def fail(*args):
            exc = RuntimeError('private-token-must-not-appear')
            exc.code = '1308'
            raise exc
        gateway.control = fail
        engine = Engine(gateway)
        r = await engine.apply('test-ac',[{'control_id':'MAIN:set_air_con_operation_mode','params':{'operation':'POWER_ON'}}])
        self.assertEqual(r['results'][0]['result']['error_code'], '1308')
        self.assertNotIn('private-token', str(r))
        self.assertEqual(engine.last_results['test-ac'], r)

    async def test_direct_apply(self):
        gateway = FakeGateway()
        engine = Engine(gateway)
        result = await engine.apply('test-ac', [{'control_id': 'MAIN:set_air_con_operation_mode', 'params': {'operation': 'POWER_ON'}}])
        self.assertEqual(gateway.calls, 1)
        self.assertEqual(result['results'][0]['result']['status'], 'ACCEPTED')

    async def test_apply_validates_all_before_sending(self):
        gateway = FakeGateway()
        with self.assertRaises(ValueError):
            await Engine(gateway).apply('test-ac', [
                {'control_id': 'MAIN:set_air_con_operation_mode', 'params': {'operation': 'POWER_ON'}},
                {'control_id': 'invalid', 'params': {}}])
        self.assertEqual(gateway.calls, 0)

    async def test_apply_unknown_not_retried(self):
        gateway = FakeGateway()
        gateway.fail_control = True
        result = await Engine(gateway).apply('test-ac', [{'control_id': 'MAIN:set_air_con_operation_mode', 'params': {'operation': 'POWER_ON'}}])
        self.assertEqual(gateway.calls, 1)
        self.assertEqual(result['results'][0]['result']['status'], 'UNKNOWN')

    def test_registry_all_sdk_types(self):
        self.assertEqual(len(device_registry()), 30)
        self.assertIn("DEVICE_WASHER", device_registry())

    async def test_compile_ac_offline(self):
        payload = await compile_control(INFO, PROFILE, "MAIN:set_air_con_operation_mode", {"operation": "POWER_ON"})
        self.assertEqual(payload, {"operation": {"airConOperationMode": "POWER_ON"}})

    async def test_invalid_value_or_method_blocked(self):
        for control, params in [("MAIN:set_air_con_operation_mode", {"operation": "BAD"}),
                                ("MAIN:_do_attribute_command", {"payload": {}})]:
            with self.assertRaises(ValueError):
                await compile_control(INFO, PROFILE, control, params)

    async def test_oven_combo_capture_contains_start_and_location(self):
        d = make_device(OVEN_INFO, OVEN_PROFILE, CaptureAPI())
        c = next(c for c in controls_for(d) if c["method"] == "set_cook_mode_with_temperature_c")
        payload = await compile_control(OVEN_INFO, OVEN_PROFILE, c["id"], {"mode": "BAKE", "target_temperature": 180})
        self.assertEqual(payload["location"]["locationName"], "OVEN")
        self.assertEqual(payload["operation"]["ovenOperationMode"], "START")
        self.assertEqual(payload["temperature"]["targetTemperature"], 180)

    async def test_oven_readonly_temperature_blocks_combo(self):
        p = deepcopy(OVEN_PROFILE)
        p["property"][0]["temperature"][0]["targetTemperature"]["mode"] = ["r"]
        d = make_device(OVEN_INFO, p, CaptureAPI())
        self.assertFalse(any(c["method"] == "set_cook_mode_with_temperature_c" for c in controls_for(d)))


class EngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_preview_then_confirm_once(self):
        e = Engine()
        p = await e.prepare("mock-ac", "/property/temperature/targetTemperature", {"value": 24.5})
        self.assertEqual(e.mock.get_state("mock-ac")["/property/temperature/targetTemperature"], 25)
        r = await e.confirm(p["ticket"])
        self.assertEqual(r["after"], 24.5)
        with self.assertRaises(ValueError):
            await e.confirm(p["ticket"])

    async def test_stale_preview_rejected(self):
        e = Engine()
        p = await e.prepare("mock-ac", "/property/temperature/targetTemperature", {"value": 24})
        e.mock.simulate(e.mock.prepare("mock-ac", "/property/temperature/targetTemperature", 23))
        with self.assertRaises(ValueError):
            await e.confirm(p["ticket"])

    async def test_expiry(self):
        e = Engine()
        p = await e.prepare("mock-ac", "/property/temperature/targetTemperature", {"value": 24})
        e.pending[p["ticket"]]["expires"] = time.monotonic()-1
        with self.assertRaises(ValueError):
            await e.confirm(p["ticket"])

    async def test_live_transport_fake_only(self):
        g = FakeGateway()
        e = Engine(g)
        p = await e.prepare("test-ac", "MAIN:set_air_con_operation_mode", {"operation": "POWER_ON"})
        self.assertEqual(g.calls, 0)
        r = await e.confirm(p["ticket"])
        self.assertEqual(g.calls, 1)
        self.assertEqual(r["status"], "ACCEPTED")

    async def test_timeout_is_unknown_not_retry(self):
        g = FakeGateway()
        g.fail_control = True
        e = Engine(g)
        p = await e.prepare("test-ac", "MAIN:set_air_con_operation_mode", {"operation": "POWER_ON"})
        r = await e.confirm(p["ticket"])
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertNotIn("do-not-expose-secret", str(r))
        self.assertEqual(g.calls, 1)


class ConfigTests(unittest.TestCase):
    def test_kr_and_phone_code(self):
        for value in ("KR", "+82", "82", "대한민국"):
            self.assertEqual(country_code(value), "KR")

    def test_no_pat_fails_without_creating_id(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                live_settings(Path(folder))
            self.assertFalse((Path(folder)/"private").exists())

    def test_errors_never_return_upstream_text(self):
        self.assertNotIn("secret", safe_error(RuntimeError("secret")))


class WebTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = create_app()
        self.server = TestServer(self.app)
        await self.server.start_server()
        self.app[HOSTS].add(f"127.0.0.1:{self.server.port}")
        self.client = TestClient(self.server)
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_config_no_token_and_kr(self):
        r = await self.client.get('/api/config')
        data = await r.json()
        self.assertEqual(data["country"], "KR")
        self.assertEqual(data["mode"], "MOCK")
        self.assertNotIn("PAT", str(data))

    async def test_csrf_and_foreign_origin_blocked(self):
        r = await self.client.post('/api/prepare', json={})
        self.assertEqual(r.status, 403)
        r = await self.client.get('/api/config', headers={"Origin": "http://evil.example"})
        self.assertEqual(r.status, 403)
        r = await self.client.get('/api/config', headers={"Host": "evil.example"})
        self.assertEqual(r.status, 403)

    async def test_http_workflow(self):
        conf = await (await self.client.get('/api/config')).json()
        headers = {"X-Demo-CSRF": conf["csrf"]}
        r = await self.client.post('/api/prepare', headers=headers, json={"device_id": "mock-fridge", "control_id": "/property/express/enabled", "params": {"value": True}})
        self.assertEqual(r.status, 200)
        p = await r.json()
        r = await self.client.post('/api/confirm', headers=headers, json={"ticket": p["ticket"]})
        self.assertEqual(r.status, 200)
        self.assertTrue((await r.json())["after"])
        r = await self.client.post('/api/confirm', headers=headers, json={"ticket": p["ticket"]})
        self.assertEqual(r.status, 400)

    async def test_unavailable_device_does_not_hide_other_devices(self):
        r = await self.client.get('/api/devices/mock-unknown')
        self.assertEqual((await r.json())["controls"], [])
        r = await self.client.get('/api/devices')
        self.assertEqual(len((await r.json())["devices"]), 7)
