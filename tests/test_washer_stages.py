import unittest
from thinq_demo.washer_match import COURSES,compare

class StageTests(unittest.TestCase):
    def test_each_course_has_supported_defaults_and_all_stages(self):
        for course in COURSES:
            facts={'purpose':course['purpose'],'temperature_c':30}
            result=compare(facts)
            candidate=next(c for c in result['candidates'] if c['id']==course['id'])
            self.assertEqual(candidate['included_stages'],['wash','rinse','spin'])
            self.assertIn(candidate['settings']['rinse_count'],course['rinses'])
            self.assertIn(candidate['settings']['spin'],course['spins'])
            self.assertEqual(facts,{'purpose':course['purpose'],'temperature_c':30})

    def test_explicit_values_override_defaults(self):
        c=compare({'purpose':'functional','temperature_c':30,'rinse_count':3,'spin':'low'})['recommended']
        self.assertEqual(c['settings']['rinse_count'],3)
        self.assertEqual(c['settings']['spin'],'low')
        self.assertEqual(c['defaulted_fields'],[])
