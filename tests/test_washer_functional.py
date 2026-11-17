import unittest
from thinq_demo.washer_match import compare
class FunctionalTests(unittest.TestCase):
 def test_course_from_material_without_past_course(self):
  r=compare(dict(purpose='functional',temperature_c=30,spin='low',course=None))
  self.assertEqual(r['recommended']['id'],'functional')
  self.assertEqual(r['recommended']['settings']['rinse_count'],2)
  self.assertIn('rinse_count',r['recommended']['defaulted_fields'])
 def test_range_does_not_hide_material(self):
  r=compare(dict(purpose='functional',temperature_c=None,temperature_description='3~40도',spin='low'))
  self.assertEqual(r['candidates'][0]['id'],'functional')
  self.assertIsNone(r['recommended']);self.assertFalse(r['can_simulate'])
 def test_unsupported_spin_not_silently_preserved(self):
  r=compare(dict(purpose='functional',temperature_c=30,spin='high'))
  self.assertFalse(r['candidates'])
