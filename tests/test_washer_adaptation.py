import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from thinq_demo import washer_journey as j


class AdaptationTests(unittest.TestCase):
    def setUp(self):
        j.SESSIONS.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(j, 'DB', Path(self.tmp.name)/'cards.sqlite3')
        self.db.start()

    def tearDown(self):
        self.db.stop()
        self.tmp.cleanup()
        j.SESSIONS.clear()

    def test_vague_request_does_not_invent_settings(self):
        r = j.create('F14WQT', {'purpose': None, 'temperature_c': None, 'spin': None})
        self.assertEqual(r['next_question']['field'], 'purpose')
        self.assertEqual(r['candidates'], [])
        self.assertFalse(r['can_run'])
        r = j.act(r['id'], 'answer', {'field': 'purpose', 'value': None})
        self.assertFalse(r['can_run'])
        self.assertIsNone(r['facts']['temperature_c'])

    def test_forgetting_spin_preserves_history_and_does_not_guess(self):
        facts = dict(purpose='functional', temperature_c=None, spin=None, spin_change='stronger',
                     remembered_behavior='탈수 버튼을 한 번 더 눌렀어')
        r = j.create('F14WQT', facts)
        self.assertEqual(r['next_question']['field'], 'spin')
        r = j.act(r['id'], 'answer', {'field':'spin', 'value':None})
        self.assertEqual(r['next_question']['field'], 'temperature_c')
        self.assertIsNone(r['facts']['spin'])
        r = j.act(r['id'], 'answer', {'field':'temperature_c', 'value':30})
        self.assertEqual(r['original_facts'], facts)
        self.assertIn('복원 아님', r['adaptation_label'])
        r = j.act(r['id'], 'select', {'course_id':'functional'})
        self.assertTrue(r['can_run'])
        self.assertEqual(r['selected_course']['settings']['spin'], 'medium')
        self.assertIn('spin', r['selected_course']['defaulted_fields'])
        r = j.act(r['id'], 'save', {'name':'모르는 탈수 그대로'})
        j.SESSIONS.clear()
        loaded = j.load(r['card_id'])
        self.assertTrue(loaded['can_run'])
        self.assertEqual(loaded['original_facts'], facts)
        self.assertEqual(loaded['unknown_fields'], ['spin'])

    def test_stale_or_unsupported_answers_rejected(self):
        r=j.create('F14WQT', dict(purpose=None, temperature_c=None))
        for data in [{'field':'temperature_c','value':40}, {'field':'purpose','value':'invented'}]:
            with self.assertRaises(ValueError):
                j.act(r['id'], 'answer', data)

    def test_unsupported_combination_is_not_bypassed(self):
        r=j.create('F14WQT', dict(purpose='wool', temperature_c=60))
        self.assertEqual(r['candidates'], [])
        self.assertIsNone(r['next_question'])
        self.assertFalse(r['can_run'])

    def test_usage_question_is_not_labeled_transfer(self):
        r=j.create('F14WQT', dict(request_kind='usage_help', purpose='functional', temperature_c=None))
        self.assertEqual(r['adaptation_label'], '새 제품 사용 방법 찾기')

if __name__ == '__main__':
    unittest.main()
