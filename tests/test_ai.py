import unittest
from unittest.mock import AsyncMock, patch
from thinq_demo.ai import execute
from thinq_demo.engine import Engine


class AITests(unittest.IsolatedAsyncioTestCase):
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
