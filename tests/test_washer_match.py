import unittest
from thinq_demo.washer_match import compare
from thinq_demo.washer import PENDING,simulate
import time

class WasherTests(unittest.TestCase):
 def facts(self,**kwargs):
  return dict(purpose='general',temperature_c=40,time_min=40,time_max=50,time_kind='observed_total',**kwargs)
 def test_compatible_then_time(self):
  f=self.facts();f['time_min']=48;f['time_max']=60
  r=compare(f)
  self.assertEqual(r['recommended']['id'],'standard')
 def test_tie_not_arbitrarily_chosen(self):
  self.assertIsNone(compare(self.facts())['recommended'])
 def test_wool_not_quick(self):
  f=self.facts();f.update(purpose='wool',temperature_c=30)
  self.assertEqual(compare(f)['recommended']['id'],'wool')
 def test_invalid_wool_temperature_blocks(self):
  f=self.facts();f['purpose']='wool'
  self.assertFalse(compare(f)['can_simulate'])
 def test_stage_not_total(self):
  f=self.facts();f['time_kind']='wash_stage'
  r=compare(f);self.assertFalse(r['time_compared']);self.assertIsNone(r['recommended'])
 def test_missing_purpose(self):
  f=self.facts();f['purpose']=None
  self.assertFalse(compare(f)['can_simulate'])
 def test_explicit_rinse_filter(self):
  r=compare(self.facts(rinse_count=3))
  self.assertEqual(r['recommended']['id'],'standard')
 def test_simulation_single_use(self):
  PENDING['unit-test']={'expires':time.monotonic()+60,'settings':{'course':'wool'}}
  self.assertFalse(simulate('unit-test')['real_device_command_sent'])
  with self.assertRaises(ValueError):simulate('unit-test')
