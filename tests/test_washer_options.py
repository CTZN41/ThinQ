import itertools
import unittest
from thinq_demo.washer_match import compare
from thinq_demo import washer_journey as j

class OptionTests(unittest.TestCase):
 def test_all_toggle_combinations(self):
  fields=['temperature_c','rinse_count','spin']
  for bits in itertools.product([False,True],repeat=3):
   hard=[k for k,on in zip(fields,bits) if on]
   for priority in ['preserve','time','fast']:
    with self.subTest(hard=hard,priority=priority):
     f=dict(purpose='general',temperature_c=40,rinse_count=3,spin='high',time_kind='observed_total',time_min=40,time_max=50)
     r=compare(f,{'hard':hard,'priority':priority})
     for c in r['candidates']:
      self.assertEqual(c['settings']['temperature_c'],40)
      self.assertEqual(c['settings']['spin'],'high')
      if 'rinse_count' in hard:self.assertEqual(c['settings']['rinse_count'],3)
     self.assertEqual(any(c['id']=='quick' for c in r['candidates']),'rinse_count' not in hard)
 def test_unresolved_spin_blocks_even_all_off(self):
  s=j.create('WW90J3000KW',dict(purpose='general',temperature_c=40,spin=None,spin_change='stronger'))
  try:
   j.act(s['id'],'update',{'preferences':{'hard':[],'priority':'fast'}})
   r=j.act(s['id'],'select',{'course_id':'quick'})
   self.assertFalse(r['can_run'])
   with self.assertRaises(ValueError):j.act(s['id'],'run',{})
   j.act(s['id'],'update',{'facts':{'spin':'high'}})
   self.assertTrue(j.act(s['id'],'select',{'course_id':'quick'})['can_run'])
  finally:j.SESSIONS.pop(s['id'],None)
 def test_material_restrictions_survive_all_off(self):
  r=compare(dict(purpose='wool',temperature_c=40,spin='high'),{'hard':[],'priority':'fast'})
  self.assertEqual([c['id'] for c in r['candidates']],['wool'])
  self.assertEqual(r['candidates'][0]['settings']['spin'],'low')
  self.assertTrue(r['candidates'][0]['changes'])
