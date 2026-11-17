"""Local experience cards, explicit choices, and reversible feedback proposals."""
import copy
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from .config import ROOT
from .washer_match import compare,COURSES
from . import washer

DB=ROOT/'private'/'washer_cards.sqlite3'
SESSIONS={}
PREF={'hard':['temperature_c','rinse_count','spin'],'priority':'preserve'}
LABELS={'temperature_c':'수온','rinse_count':'헹굼','spin':'탈수'}

@contextmanager
def connect():
 DB.parent.mkdir(exist_ok=True)
 conn=sqlite3.connect(DB)
 try:
  with conn:
   conn.execute('CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY, name TEXT NOT NULL, data TEXT NOT NULL)')
   yield conn
 finally:
  conn.close()

def list_cards():
 with connect() as conn:
  return [{'id':i,'name':n,**json.loads(d)} for i,n,d in conn.execute('SELECT id,name,data FROM cards ORDER BY rowid DESC')]

def event(s,kind,text):
 s['history'].append({'at':time.strftime('%Y-%m-%dT%H:%M:%S'),'kind':kind,'text':text})

def create(source,facts):
 now=time.monotonic()
 for sid in list(SESSIONS):
  if SESSIONS[sid]['expires']<now:del SESSIONS[sid]
 if len(SESSIONS)>=100:raise ValueError('세션 수 초과')
 sid=secrets.token_urlsafe(24)
 SESSIONS[sid]={'id':sid,'source':source,'facts':copy.deepcopy(facts),'preferences':copy.deepcopy(PREF),
                'selected':None,'proposal':None,'card_id':None,'history':[],'expires':now+7200}
 event(SESSIONS[sid],'extract','사용자가 입력한 경험에서 추출. 구형 제품 사양 검증과 별개입니다.')
 return view(SESSIONS[sid])

def get(sid):
 s=SESSIONS.get(sid)
 if not s or s['expires']<time.monotonic():raise ValueError('세션 만료. 카드를 불러오거나 다시 분석하세요.')
 s['expires']=time.monotonic()+7200
 return s

def view(s):
 result=compare(s['facts'],s['preferences'])
 selected=next((c for c in result['candidates'] if c['id']==s['selected']),None)
 return {**copy.deepcopy(s),**result,'selected_course':selected,'can_run':selected is not None and selected['settings']['temperature_c'] is not None and not result['needs_spin_confirmation']}

async def begin(source,experience):
 r=await washer.analyze(source,experience)
 # Legacy analysis tokens are not used in the explicit-choice workflow.
 if r['token']:washer.PENDING.pop(r['token'],None)
 return create(source,r['facts'])

def act(sid,action,data):
 s=get(sid)
 if action=='update':
  patch=data.get('facts',{})
  allowed={'purpose','temperature_c','course','rinse_count','spin','time_kind','time_min','time_max','drying_included'}
  if not isinstance(patch,dict) or not set(patch)<=allowed:raise ValueError('허용되지 않는 답변')
  f={**s['facts'],**patch}
  pref=data.get('preferences',s['preferences'])
  compare(f,pref)
  s['facts']=f;s['preferences']=copy.deepcopy(pref);s['selected']=None;s['proposal']=None
  event(s,'answer','추가 답변·유지 조건·우선순위 반영. 이전 선택을 해제했습니다.')
 elif action=='select':
  result=view(s);cid=data.get('course_id')
  if cid not in [c['id'] for c in result['candidates']]:raise ValueError('지원 후보가 아닙니다.')
  s['selected']=cid;s['proposal']=None
  event(s,'select','사용자가 후보 선택: '+cid)
 elif action=='run':
  result=view(s)
  if not result['can_run']:raise ValueError('후보와 수온을 확정하세요.')
  event(s,'simulate','가상 시작: '+json.dumps(result['selected_course']['settings'],ensure_ascii=False))
 elif action=='save':
  if not view(s)['can_run']:raise ValueError('저장할 설정을 먼저 선택하세요.')
  name=data.get('name','').strip()
  if not 1<=len(name)<=60:raise ValueError('카드 이름은 1~60자')
  s['card_id']=s['card_id'] or secrets.token_hex(12)
  event(s,'save','경험 카드 로컬 저장: '+name)
  payload={k:copy.deepcopy(s[k]) for k in ['source','facts','preferences','selected','history']}
  payload.update({'profile':'LIFEPRINT-WASHER-DEMO-v1','evidence':'합성 코스 가정 / 사용자 경험','result_verified':False})
  with connect() as conn:conn.execute('INSERT OR REPLACE INTO cards VALUES(?,?,?)',(s['card_id'],name,json.dumps(payload,ensure_ascii=False)))
 elif action=='feedback':
  kind=data.get('kind')
  if kind not in ['wrinkles','wet','satisfied']:raise ValueError('피드백 종류 오류')
  if not view(s)['can_run']:raise ValueError('후보를 먼저 선택하세요.')
  s['proposal']=None
  if kind=='satisfied':
   event(s,'feedback','사용자 만족 보고. 물리적 성능 검증을 의미하지 않습니다.')
  else:
   c=view(s)['selected_course'];spin=c['settings']['spin'];levels=['low','medium','high']
   target=None
   if spin in levels:
    i=levels.index(spin)+(-1 if kind=='wrinkles' else 1)
    if 0<=i<len(levels) and levels[i] in c['spins']:target=levels[i]
   if 'spin' in s['preferences']['hard']:
    event(s,'feedback','탈수는 필수 유지 조건입니다. 조건을 바꾸기 전에는 조정안을 만들지 않습니다.')
   elif target is None:
    event(s,'feedback','현재 탈수 단계가 없거나 조절 범위 밖입니다. 추가 확인이 필요합니다.')
   else:
    s['proposal']={'field':'spin','before':spin,'after':target,'reason':'탈수 한 단계 조정 후보. 구김·물기의 원인을 확정하거나 개선을 보장하지 않습니다.'}
    event(s,'feedback','조정안만 생성: '+json.dumps(s['proposal'],ensure_ascii=False))
 elif action=='accept_feedback':
  proposal=s['proposal']
  if not proposal:raise ValueError('조정안 없음')
  s['facts']['spin']=proposal['after'];s['proposal']=None
  if not view(s)['can_run']:raise ValueError('조정 후 지원되지 않는 조합')
  event(s,'adjust','사용자가 탈수 조정 승인: '+str(proposal['before'])+' → '+str(proposal['after'])+'; 다른 설정은 유지')
 else:raise ValueError('알 수 없는 작업')
 return view(s)

def load(card_id):
 with connect() as conn:row=conn.execute('SELECT data FROM cards WHERE id=?',(card_id,)).fetchone()
 if not row:raise ValueError('카드 없음')
 card=json.loads(row[0]);v=create(card['source'],card['facts']);s=get(v['id'])
 s.update({'preferences':card['preferences'],'selected':card['selected'],'history':card['history'],'card_id':card_id})
 event(s,'load','저장한 경험을 현재 데모 프로필로 재검증해 불러왔습니다.')
 return view(s)
