import unittest
from unittest.mock import AsyncMock, patch
from thinq_demo.ai import execute
from thinq_demo.engine import Engine


class AITests(unittest.IsolatedAsyncioTestCase):
    async def test_state_change_during_generation_blocked(self):
        engine = Engine()
        async def changed(*args):
            await engine.apply('mock-ac', [{'control_id':'/property/temperature/targetTemperature','params':{'value':28}}])
            return {'message':'낮춥니다', 'changes':[{'control_id':'/property/temperature/targetTemperature','value':24}]}
        with patch('thinq_demo.ai.generate', side_effect=changed):
            with self.assertRaisesRegex(ValueError, '상태가 바뀌었습니다'):
                await execute(engine,'mock-ac','현재보다 1도 낮춰줘')
        self.assertEqual((await engine.detail('mock-ac'))['state']['/property/temperature/targetTemperature'],28)

    async def test_offline_stops_before_paid_call(self):
        with patch('thinq_demo.ai.generate', AsyncMock()) as generate:
            with self.assertRaises(ValueError):
                await execute(Engine(),'mock-offline','켜줘')
            generate.assert_not_called()

    async def test_malformed_plan_blocked(self):
        with patch('thinq_demo.ai.generate', AsyncMock(return_value={'message':'설정','changes':[{'value':24}]})):
            with self.assertRaises(ValueError):
                await execute(Engine(),'mock-ac','24도로')

    async def test_generated_settings_applied(self):
        engine = Engine()
        plan = {'message': '24도로 설정합니다.', 'changes': [
            {'control_id': '/property/operation/airConOperationMode', 'value': 'POWER_ON'},
            {'control_id': '/property/temperature/targetTemperature', 'value': 24}]}
        with patch('thinq_demo.ai.generate', AsyncMock(return_value=plan)):
            result = await execute(engine, 'mock-ac', '켜고 24도로 맞춰줘')
        self.assertTrue(result['applied'])
        detail = await engine.detail('mock-ac')
        self.assertEqual(detail['state']['/property/temperature/targetTemperature'], 24)

    async def test_invalid_output_changes_nothing(self):
        engine = Engine()
        before = (await engine.detail('mock-ac'))['state'].copy()
        plan = {'message': '설정', 'changes': [
            {'control_id': '/property/operation/airConOperationMode', 'value': 'POWER_ON'},
            {'control_id': '/property/temperature/targetTemperature', 'value': 99}]}
        with patch('thinq_demo.ai.generate', AsyncMock(return_value=plan)):
            with self.assertRaises(ValueError):
                await execute(engine, 'mock-ac', '99도')
        self.assertEqual(before, (await engine.detail('mock-ac'))['state'])

    async def test_clarification_no_apply(self):
        engine = Engine()
        with patch('thinq_demo.ai.generate', AsyncMock(return_value={'message': '몇 도로 할까요?', 'changes': []})):
            self.assertFalse((await execute(engine, 'mock-ac', '시원하게'))['applied'])

    async def test_live_blocked_before_generation(self):
        with patch('thinq_demo.ai.generate', AsyncMock()) as generate:
            with self.assertRaises(ValueError):
                await execute(Engine(object()), 'anything', '켜줘')
            generate.assert_not_called()
