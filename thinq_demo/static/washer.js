'use strict';
const $=id=>document.getElementById(id);let current=null,csrf='',busy=false;
const labels={temperature_c:'수온',rinse_count:'헹굼',spin:'탈수'},vals={low:'약',medium:'중',high:'강'};
const text=v=>v===null||v===undefined?'미지정':vals[v]||v;
function el(tag,t){const n=document.createElement(tag);n.textContent=t;return n;}
async function request(data){if(!csrf)csrf=(await(await fetch('/api/config')).json()).csrf;const r=await fetch('/api/washer/flow',{method:'POST',headers:{'Content-Type':'application/json','X-Demo-CSRF':csrf},body:JSON.stringify(data)});const d=await r.json();if(!r.ok)throw Error(d.error);return d;}
async function refreshCards(){const r=await fetch('/api/washer/cards');const d=await r.json();$('cards').replaceChildren();for(const c of d.cards){const b=el('button',c.name+' · '+c.source);b.onclick=()=>perform({action:'load',card_id:c.id},()=>{$('cardName').value=c.name;});$('cards').append(b);}if(!d.cards.length)$('cards').textContent='저장한 경험이 아직 없어요.';}
async function perform(data,after){
 if(busy)return;busy=true;
 document.querySelectorAll('button').forEach(b=>b.disabled=true);
 document.querySelectorAll('input,select,textarea').forEach(e=>e.disabled=true);
 $('progress').textContent='처리 중…';
 let success=false;
 try{current=await request({session_id:current?.id,...data});await refreshCards();success=true;}
 catch(e){$('progress').textContent=e.message;}
 finally{busy=false;document.querySelectorAll('input,select,textarea').forEach(e=>e.disabled=false);$('analyze').disabled=false;document.querySelectorAll('#cards button').forEach(b=>b.disabled=false);if(current)render(current);}
 if(success){
  $('simulation').textContent='';$('saved').textContent='';$('progress').textContent='';
  if(['begin','load'].includes(data.action)){$('inputPanel').open=false;document.querySelector('.saved-drawer').open=false;}
  if(['begin','load','update'].includes(data.action))$('conditions').open=!current.candidates.length||current.facts.temperature_c===null||current.needs_spin_confirmation;
  if(data.action==='select')$('alternatives').open=false;
  if(after)after();
 }
}

function render(d){$('journey').hidden=false;$('summary').textContent=`${d.source}에서 사용했던 방법을 바탕으로 비교했어요.`;$('source').value=d.source;
for(const k of ['purpose','temperature_c','rinse_count','spin','time_kind','time_min','time_max'])$(k).value=d.facts[k]??'';
for(const [id,key]of [['hard_temp','temperature_c'],['hard_rinse','rinse_count'],['hard_spin','spin']])$(id).checked=d.preferences.hard.includes(key);
$('priority').value=d.preferences.priority;
const missing=d.needs_confirmation;
$('questions').replaceChildren(...(missing?[d.needs_spin_confirmation?(d.facts.spin_rpm?'이 기기의 RPM과 약·중·강 대응을 아직 알 수 없어요. 사용할 탈수 단계를 직접 선택해 주세요.':'탈수를 바꾼 뒤, 약·중·강 중 어떤 단계로 사용했나요?'):'용도와 수온을 확인하면 방법을 비교할 수 있어요.']:!d.candidates.length?['조건에 맞는 방법이 없어요. 유지할 조건을 확인해 주세요.']:!d.recommended&&!d.selected?['비슷한 방법이 여러 개예요. 원하는 방법을 골라주세요.']:[]).map(q=>el('li',q)));
if(d.facts.purpose==='functional'&&d.facts.temperature_c===null&&!d.needs_spin_confirmation)$('questions').replaceChildren(el('li',`기능성 의류 위주로 이해했어요. ${d.facts.temperature_description?'“'+d.facts.temperature_description+'”에서 ':''}이번에 사용할 수온을 선택해 주세요.`));
if(d.facts.mixed_laundry)$('questions').append(el('li','주로 언급한 의류 기준의 후보예요. 섞인 옷 전체에 적합한지는 확인되지 않았어요.'));
if(missing||!d.candidates.length)$('conditions').open=true;
const featured=d.selected_course||d.recommended;
$('summary').textContent=d.recommendation_reason;
$('candidates').replaceChildren();$('otherCandidates').replaceChildren();
for(const c of d.candidates){const box=el('article','');box.className='candidate';box.append(el('h3',c.name.replace(' 데모','')+(d.recommended?.id===c.id?' · 추천':'')),el('p',`약 ${c.minutes}분 · 수온 ${text(c.settings.temperature_c)}℃ · 헹굼 ${text(c.settings.rinse_count)}회 · 탈수 ${text(c.settings.spin)}`));
box.append(el('p',c.changes.length?c.changes.map(x=>`${labels[x.field]} ${text(x.before)} → ${text(x.after)}`).join(' / '):'명시한 설정은 그대로 유지해요.'));
if(d.unspecified?.length)box.append(el('p',d.unspecified.map(k=>labels[k]).join('·')+'는 입력되지 않아 정하지 않았어요.'));
if(c.time_gap!==null&&c.time_gap>0)box.append(el('p',`이전 시간 범위와 ${c.time_gap}분 차이가 있어요.`));
const b=el('button',d.selected===c.id?'선택한 방법':'이 방법 선택');b.disabled=d.selected===c.id;b.onclick=()=>perform({action:'select',course_id:c.id});box.append(b);(featured&&featured.id!==c.id?$('otherCandidates'):$('candidates')).append(box);}
$('alternatives').hidden=!$('otherCandidates').children.length;
$('usePanel').hidden=!d.can_run;$('selected').textContent=d.selected_course?`${d.selected_course.name.replace(' 데모','')}으로 진행할게요.`:'';
for(const id of ['simulate','save','feedback'])$(id).disabled=!d.can_run;$('update').disabled=false;
$('feedbackPanel').hidden=!d.history.some(h=>h.kind==='simulate');
$('proposal').textContent=d.proposal?`${labels[d.proposal.field]}를 ${text(d.proposal.before)}에서 ${text(d.proposal.after)}으로 바꿔볼까요? 효과는 사용 후 확인해 주세요.`:'';$('accept').hidden=!d.proposal;$('accept').disabled=false;
}
$('transfer').onsubmit=e=>{e.preventDefault();$('simulation').textContent='';$('saved').textContent='';perform({action:'begin',source:$('source').value,experience:$('experience').value});};
$('answers').onsubmit=e=>{e.preventDefault();const facts={};for(const k of ['temperature_c','rinse_count','time_min','time_max'])facts[k]=$(k).value===''?null:Number($(k).value);for(const k of ['purpose','spin','time_kind'])facts[k]=$(k).value||null;perform({action:'update',facts,preferences:{hard:[['hard_temp','temperature_c'],['hard_rinse','rinse_count'],['hard_spin','spin']].filter(([id])=>$(id).checked).map(([,k])=>k),priority:$('priority').value}});};
$('simulate').onclick=()=>perform({action:'run'},()=>{$('simulation').textContent='체험을 시작했어요. 실제 세탁기는 작동하지 않아요.';});
$('save').onclick=()=>perform({action:'save',name:$('cardName').value},()=>{$('saved').textContent='저장했어요. 다음에는 불러와서 사용할 수 있어요.';});
$('feedback').onclick=()=>perform({action:'feedback',kind:$('feedbackKind').value},()=>{if(!current.proposal)$('progress').textContent=$('feedbackKind').value==='satisfied'?'만족한 경험으로 기록했어요.':'유지 조건 또는 지원 범위 때문에 조정할 수 없어요.';});
$('accept').onclick=()=>perform({action:'accept_feedback'});
refreshCards().catch(e=>$('progress').textContent=e.message);
