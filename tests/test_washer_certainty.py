import unittest
from thinq_demo.washer_match import compare
class CertaintyTests(unittest.TestCase):
 def test_no_recommendation_with_missing_temperature(self):
  r=compare(dict(purpose='wool',temperature_c=None))
  self.assertIsNone(r['recommended']);self.assertEqual(r['recommendation_status'],'needs_confirmation')
 def test_relative_never_badged_recommended(self):
  r=compare(dict(purpose='general',temperature_c=40,rinse_count=3,spin_change='stronger'))
  self.assertIsNone(r['recommended']);self.assertFalse(r['can_simulate'])
 def test_rpm_requires_mapping(self):
  r=compare(dict(purpose='general',temperature_c=40,rinse_count=3,spin_rpm=1200))
  self.assertTrue(r['needs_spin_confirmation']);self.assertIsNone(r['recommended'])
 def test_unknown_optional_not_invented(self):
  r=compare(dict(purpose='wool',temperature_c=30))
  self.assertEqual(r['unspecified'],['rinse_count','spin'])
  self.assertIsNone(r['recommended']['settings']['spin'])
 def test_unsupported_has_reason(self):
  r=compare(dict(purpose='wool',temperature_c=60))
  self.assertEqual(r['recommendation_status'],'unsupported')
 def test_tie_not_certainty(self):
  r=compare(dict(purpose='general',temperature_c=40))
  self.assertEqual(r['recommendation_status'],'tie')
