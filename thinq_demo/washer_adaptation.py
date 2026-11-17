"""One question at a time; unknown history stays unknown."""
PURPOSES=[('general','일반 옷'),('functional','운동복·기능성 옷'),('towels','수건'),('wool','울'),('delicate','섬세한 옷')]

def guidance(session, result):
    facts=session['facts']; unknown=session.get('unknown_fields',[])
    question=None
    if facts.get('purpose') not in dict(PURPOSES):
        question={'field':'purpose','text':'이번에는 어떤 빨래를 하려고 하나요?',
                  'choices':[{'value':v,'label':label} for v,label in PURPOSES], 'allow_unknown':True}
        if 'purpose' in unknown:
            question['text']='의류 종류가 확인되면 방법을 고를 수 있어요. 확인 후 아래에서 선택해 주세요.'
            question['allow_unknown']=False
    elif result['needs_spin_confirmation']:
        question={'field':'spin','text':'바꾼 뒤의 탈수 단계가 기억나나요? 버튼 횟수나 RPM만으로는 단계를 알 수 없어요.',
                  'choices':[{'value':v,'label':label} for v,label in [('low','약'),('medium','중'),('high','강')]], 'allow_unknown':True}
    elif facts.get('temperature_c') is None and result['candidates']:
        # These are the synthetic target profile's choices, not reconstructed old settings.
        temperatures=sorted({t for c in result['candidates'] for t in c['temperatures']})
        question={'field':'temperature_c', 'text':'이번 체험에서 사용할 수온을 선택해 주세요. 예전 수온을 기억할 필요는 없어요.',
                  'choices':[{'value':v,'label':str(v)+'℃'} for v in temperatures], 'allow_unknown':False}
    new_setup=bool(unknown or session.get('new_choices'))
    kind=facts.get('request_kind')
    label={'usage_help':'새 제품 사용 방법 찾기','result_problem':'사용 결과에 맞는 방법 찾기'}.get(kind,'기억하는 세탁 방식 비교')
    if new_setup:label='새 시작 설정 선택 · 이전 설정 복원 아님'
    return {'next_question':question,'adaptation_label':label,
            'adaptation_note':'구형 모델의 버튼 동작·기본값은 아직 검증되지 않았어요. 후보는 가상 제품 기준이며 실제 세탁 결과를 보장하지 않아요.',
            'remembered_behavior':facts.get('remembered_behavior'),
            'unknown_fields':list(unknown), 'new_choices':session.get('new_choices',{})}
