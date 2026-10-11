import pytest
from app.services import testing_engine as engine
from scripts.verify_hybrid_testing import SOLUTIONS
from tests.conftest import register, SURVEY

@pytest.mark.parametrize('grade', ['intern', 'junior', 'middle', 'senior'])
def test_contest_weights_and_perfect_real_solutions(grade):
    items = engine.build_items('backend', grade, 17)
    assert len(items) == 3
    assert [(i['base_weight'], i['bonus_weight']) for i in items] == [(15,5),(20,10),(35,15)]
    result = engine.score_attempt(items, {i['id']: SOLUTIONS[i['template_id']] for i in items})
    assert result['score'] == 100
    assert [i['score'] for i in result['items']] == [20,30,50]
    assert all(i['fraction'] == 1 for i in result['items'])
    assert all('tests' not in engine.public_item(i)['code'] for i in items)
    assert [engine.public_item(i)['max_score'] for i in items] == [20,30,50]

@pytest.mark.parametrize('fractions,expected', [([0,0,.8],28),([1,1,1],100),([.8,.8,.8],56),([1,0,0],20),([0,1,0],30),([0,0,1],50),([0,0,0],0)])
def test_partial_and_bonus(monkeypatch, fractions, expected):
    items = engine.build_items('backend','junior',5)
    values = {i['id']: f for i,f in zip(items,fractions)}
    monkeypatch.setattr(engine,'grade_item',lambda item,answer:(values[item['id']], {'status':'partial'}))
    result = engine.score_attempt(items,{})
    assert result['score'] == expected
    assert all(0 <= i['fraction'] <= 1 for i in result['items'])

def test_legacy_attempts_keep_old_scoring():
    items = engine.build_items('backend','junior',5)
    for i in items:
        del i['base_weight']; del i['bonus_weight']; i['weight'] = 2
    answers = {i['id']: SOLUTIONS[i['template_id']] for i in items[:1]}
    assert engine.score_attempt(items,answers)['score'] == 33.3

def test_damaged_matrix_rejected():
    items = engine.build_items('backend','junior',5)
    items[2]['bonus_weight'] = 99
    with pytest.raises(ValueError, match='матрица'):
        engine.score_attempt(items,{})

def test_api_returns_points_and_retains_grade_logic(client, db):
    from app.models import TestAttempt
    h = register(client, 'scoring@test.ru')
    client.post('/api/candidate/survey',json=SURVEY,headers=h)
    response = client.post('/api/testing/attempts',json={'specialization':'backend','target_grade':'junior'},headers=h)
    assert response.status_code == 201
    payload=response.json()
    assert [i['max_score'] for i in payload['items']] == [20,30,50]
    db.expire_all(); items=db.get(TestAttempt,payload['id']).items
    answers={i['id']:SOLUTIONS[i['template_id']] for i in items}
    result=client.post(f"/api/testing/attempts/{payload['id']}/submit",json={'answers':answers},headers=h)
    assert result.status_code == 200, result.text
    assert result.json()['score'] == 100
    assert [i['score'] for i in result.json()['items']] == [20,30,50]
    assert result.json()['decision']['grade_after'] == 'junior'


def test_four_of_five_hidden_tests_gives_28_real_runner():
    items = engine.build_items('backend','junior',5)
    items[2]['code']['function_name'] = 'solve'
    items[2]['code']['tests'] = [{'args':[n], 'expected':n if n < 4 else 99} for n in range(5)]
    result = engine.score_attempt(items, {'q3':'def solve(n):\n    return n\n'})
    assert result['score'] == 28
    assert result['items'][2]['passed'] == 4
    assert result['items'][2]['total'] == 5
