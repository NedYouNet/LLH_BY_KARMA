import pytest
from app.services.testing_engine import build_items, score_attempt, public_item
from scripts.verify_hybrid_testing import solution_for
from tests.conftest import register, SURVEY
from app.models import TestAttempt

SPECS=['backend','frontend','data_science','qa','devops']
GRADES=['intern','junior','middle','senior']

@pytest.mark.parametrize('spec',SPECS)
@pytest.mark.parametrize('grade',GRADES)
def test_difficulties_match_order_weights_and_real_solutions(spec,grade):
    items=build_items(spec,grade,171,total=99)
    assert len(items)==3
    assert [i['difficulty'] for i in items]==['easy','medium','hard']
    assert len({i['template_id'] for i in items})==3
    assert [i['weight'] for i in items]==[20,30,50]
    assert len({i['level'] for i in items})==1
    assert items==build_items(spec,grade,171,total=1)
    result=score_attempt(items,{i['id']:solution_for(i) for i in items})
    assert [i['score'] for i in result['items']]==[20,30,50]
    assert result['score']==100
    for i in items:
        visible=public_item(i)
        assert 'tests' not in visible['code']
        assert 'answer' not in visible

@pytest.mark.parametrize('spec',SPECS)
def test_api_new_directions_code_check_and_submit(spec,client,db):
    h=register(client,f'{spec}@all.ru')
    response=client.post('/api/candidate/survey',json={**SURVEY,'specialization':spec},headers=h)
    assert response.status_code==200,response.text
    response=client.post('/api/testing/attempts',json={'specialization':spec,'target_grade':'middle'},headers=h)
    assert response.status_code==201,response.text
    data=response.json()
    assert [i['difficulty'] for i in data['items']]==['easy','medium','hard']
    db.expire_all(); items=db.get(TestAttempt,data['id']).items
    code=solution_for(items[2])
    checked=client.post(f"/api/testing/attempts/{data['id']}/check",json={'item_id':'q3','code':code},headers=h)
    assert checked.status_code==200,checked.text
    assert checked.json()['passed']==checked.json()['total']
    result=client.post(f"/api/testing/attempts/{data['id']}/submit",json={'answers':{i['id']:solution_for(i) for i in items}},headers=h)
    assert result.status_code==200,result.text
    assert result.json()['score']==100
    assert result.json()['items'][2]['difficulty']=='hard'
