import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from thinq_demo import washer_journey as j

class JourneyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.p=patch.object(j,'DB',Path(self.temp.name)/'cards.sqlite3');self.p.start()
  j.SESSIONS.clear()
  self.f=dict(purpose='general',temperature_c=40,rinse_count=3,spin='high',time_min=40,time_max=50,time_kind='observed_total')
  self.sid=j.create('WW90J3000KW',self.f)['id']
 def tearDown(self):
  self.p.stop();self.temp.cleanup();j.SESSIONS.clear()
 def select(self):
  j.act(self.sid,'update',{'preferences':{'hard':['temperature_c'],'priority':'fast'}})
  return j.act(self.sid,'select',{'course_id':'quick'})
 def test_explicit_choice_required(self):
  with self.assertRaises(ValueError):j.act(self.sid,'run',{})
 def test_soft_changes_are_disclosed(self):
  r=self.select();c=r['selected_course']
  self.assertEqual(c['settings']['temperature_c'],40)
  self.assertEqual(c['changes'],[{'field':'rinse_count','before':3,'after':2}])
 def test_proposal_requires_accept_and_changes_only_spin(self):
  before=self.select()['selected_course']['settings']
  r=j.act(self.sid,'feedback',{'kind':'wrinkles'})
  self.assertEqual(r['selected_course']['settings'],before)
  r=j.act(self.sid,'accept_feedback',{})
  self.assertEqual(r['selected_course']['settings'],{**before,'spin':'medium'})
 def test_hard_spin_blocks_adjustment(self):
  j.act(self.sid,'select',{'course_id':'standard'})
  self.assertIsNone(j.act(self.sid,'feedback',{'kind':'wrinkles'})['proposal'])
 def test_save_reuse_after_memory_cleared(self):
  self.select();r=j.act(self.sid,'save',{'name':'test'})
  j.SESSIONS.clear();loaded=j.load(r['card_id'])
  self.assertTrue(loaded['can_run']);self.assertEqual(loaded['selected'],'quick')
  j.act(loaded['id'],'save',{'name':'updated'})
  self.assertEqual(len(j.list_cards()),1)
 def test_updated_answers_clear_selection(self):
  self.select();r=j.act(self.sid,'update',{'facts':{'purpose':'wool'}})
  self.assertFalse(r['can_run']);self.assertIsNone(r['selected'])
