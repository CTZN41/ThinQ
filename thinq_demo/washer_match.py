"""Synthetic profiles only: NOT specifications of a real LG model."""
import math

COURSES=[
 {'id':'functional','name':'기능성 의류 데모','purpose':'functional','temperatures':[20,30,40],'minutes':50,'rinses':[1,2,3],'spins':['low','medium']},
 {'id':'standard','name':'일반 의류 데모','purpose':'general','temperatures':[20,30,40,60],'minutes':55,'rinses':[1,2,3],'spins':['low','medium','high']},
 {'id':'quick','name':'일반 의류 단축 데모','purpose':'general','temperatures':[20,30,40],'minutes':35,'rinses':[1,2],'spins':['low','medium','high']},
 {'id':'wool','name':'울 보호 데모','purpose':'wool','temperatures':[20,30],'minutes':42,'rinses':[1,2],'spins':['low']},
 {'id':'delicate','name':'섬세 의류 데모','purpose':'delicate','temperatures':[20,30,40],'minutes':48,'rinses':[1,2,3],'spins':['low']},
 {'id':'towels','name':'수건 데모','purpose':'towels','temperatures':[30,40,60],'minutes':65,'rinses':[2,3],'spins':['medium','high']}]

def number(v):return type(v) in (int,float) and math.isfinite(v)

def compare(facts, preferences=None):
 purpose=facts.get('purpose');temp=facts.get('temperature_c');rinse=facts.get('rinse_count');spin=facts.get('spin')
 questions=[]
 unresolved_spin=(facts.get('spin_change') in ('stronger','weaker') or facts.get('spin_rpm') is not None) and spin is None
 if unresolved_spin:questions.append('탈수를 바꾼 뒤 사용한 단계가 약·중·강 중 무엇이었나요?')
 if purpose not in {'general','wool','delicate','towels','functional'}:questions.append('의류 종류를 알려주세요.')
 if temp is not None and (not number(temp) or not 0<=temp<=100):raise ValueError('수온 형식 오류')
 if rinse is not None and (type(rinse) is not int or not 1<=rinse<=10):raise ValueError('헹굼 형식 오류')
 if spin not in (None,'low','medium','high'):raise ValueError('탈수 형식 오류')
 lo=facts.get('time_min');hi=facts.get('time_max')
 if lo is not None or hi is not None:
  if not number(lo) or not number(hi) or not 0<lo<=hi<=1440:raise ValueError('시간 형식 오류')
 known=lo is not None and facts.get('time_kind')=='observed_total'
 preferences=preferences or {'hard':['temperature_c','rinse_count','spin'],'priority':'preserve'}
 hard=preferences['hard'];priority=preferences['priority']
 if not isinstance(hard,list) or any(k not in ['temperature_c','rinse_count','spin'] for k in hard) or priority not in ['preserve','time','fast']:raise ValueError('선호 조건 오류')
 candidates=[];excluded=[]
 for c in COURSES:
  reasons=[]
  if purpose!=c['purpose']:reasons.append('용도 불일치 또는 미확인')
  if temp is not None and temp not in c['temperatures'] and 'temperature_c' in hard:reasons.append('필수 수온 미지원')
  if rinse is not None and rinse not in c['rinses'] and 'rinse_count' in hard:reasons.append('필수 헹굼 횟수 미지원')
  if spin is not None and spin not in c['spins'] and 'spin' in hard:reasons.append('필수 탈수 단계 미지원')
  if reasons:excluded.append({'name':c['name'],'reasons':reasons});continue
  new_temp=temp if temp is None or temp in c['temperatures'] else min(c['temperatures'],key=lambda v:abs(v-temp))
  new_rinse=rinse if rinse is None or rinse in c['rinses'] else min(c['rinses'],key=lambda v:abs(v-rinse))
  levels=['low','medium','high']
  new_spin=spin if spin is None or spin in c['spins'] else min(c['spins'],key=lambda v:abs(levels.index(v)-levels.index(spin)))
  changes=[{'field':k,'before':a,'after':b} for k,a,b in [('temperature_c',temp,new_temp),('rinse_count',rinse,new_rinse),('spin',spin,new_spin)] if a!=b]
  candidates.append({**c,'time_gap':max(lo-c['minutes'],c['minutes']-hi,0) if known else None,'changes':changes,
   'settings':{'course':c['id'],'temperature_c':new_temp,'rinse_count':new_rinse,'spin':new_spin}})
 def rank(c):
  gap=c['time_gap'] if known else 0
  if priority=='fast':return (c['minutes'],len(c['changes']))
  if priority=='time':return (gap,len(c['changes']))
  return (len(c['changes']),gap)
 candidates.sort(key=rank)
 chosen=candidates[0] if candidates else None
 if temp is None:questions.append('유지할 수온을 알려주세요. 임의 기본 수온을 생성하지 않습니다.')
 if facts.get('time_kind') in ('unknown','wash_stage','scheduled'):questions.append('전체 세탁 소요 시간인가요? 단계 시간·예약 시간과 전체 시간을 비교하지 않습니다.')
 if len(candidates)>1 and rank(candidates[0])==rank(candidates[1]):
  chosen=None;questions.append('동등한 후보가 여럿입니다. 전체 시간 등 선택 기준을 추가하거나 원하는 후보를 명시해주세요.')
 # A top-ranked candidate is not a recommendation until required facts are known.
 needs_confirmation=temp is None or unresolved_spin or purpose not in {'general','wool','delicate','towels','functional'}
 if needs_confirmation:chosen=None
 if needs_confirmation:status='needs_confirmation';explanation='필요한 조건을 확인한 뒤 추천할게요.'
 elif not candidates:status='unsupported';explanation='유지할 조건을 모두 만족하는 방법이 없어요.'
 elif chosen is None:status='tie';explanation='현재 조건으로는 우열을 가릴 수 없어 직접 선택이 필요해요.'
 else:
  status='recommended'
  explanation={'preserve':'입력한 설정을 가장 적게 바꾸는 방법이에요.','time':'관찰한 전체 시간 범위에 가장 가까운 방법이에요.','fast':'조건에 맞는 방법 중 소요 시간이 가장 짧아요.'}[priority]
  if priority=='time' and not known:explanation='전체 시간이 없어 설정 변경이 가장 적은 방법을 골랐어요.'
  if len(candidates)==1:explanation='유지 조건과 용도를 모두 만족하는 유일한 방법이에요.'
 unspecified=[k for k,v in [('rinse_count',rinse),('spin',spin)] if v is None]
 return {'candidates':candidates,'excluded':excluded,'recommended':chosen,'questions':questions,
  'recommendation_status':status,'recommendation_reason':explanation,'needs_confirmation':needs_confirmation,'unspecified':unspecified,
  'can_simulate':chosen is not None and temp is not None and not unresolved_spin,'needs_spin_confirmation':unresolved_spin,'time_compared':known,
  'mode':'경험 기반 추천' if not facts.get('course') else '사용자 코스 진술 기반 비교 · 구형 제약 미검증',
  'evidence':'모든 후보 코스·옵션·시간은 데모 가정입니다. 실제 FX25GFG 사양이나 조리·세탁 성능이 아닙니다.'}
