"""Контракт гибридных задач команды, реальные решения и старые попытки."""
import copy
import pytest

from app.reference import GRADE_LEVEL
from app.services.testing_engine import build_items, grade_item, public_item, score_attempt
from tests.conftest import SURVEY, register


from scripts.verify_hybrid_testing import SOLUTIONS


@pytest.mark.parametrize('grade', GRADE_LEVEL)
def test_three_tasks_selected_grade_and_all_families(grade):
    level = GRADE_LEVEL[grade]
    from app.services.testing_engine import template_difficulty
    from app.testing_bank import templates_for
    expected = {t.id for t in templates_for('backend') if t.level == level and template_difficulty(t)}
    for seed in range(250):
        items = build_items('backend', grade, seed)
        assert len(items) == 3
        assert {i['template_id'] for i in items} == expected
        assert [i['difficulty'] for i in items] == ['easy','medium','hard']
        assert all(i['level'] == level and i['kind'] == 'code' for i in items)
        assert items == build_items('backend', grade, seed)
        for item in items:
            public = public_item(item)
            assert 'answer' not in public and 'template_id' not in public
            assert 'tests' not in public['code']


@pytest.mark.parametrize('spec', ['frontend', 'qa', 'devops', 'data_science'])
@pytest.mark.parametrize('grade', GRADE_LEVEL)
def test_other_specializations_use_difficulty_contests(spec, grade):
    for seed in range(20):
        items = build_items(spec, grade, seed)
        assert len(items) == 3
        assert [i["difficulty"] for i in items] == ["easy", "medium", "hard"]
        assert all(i['kind'] == 'code' for i in items)


@pytest.mark.parametrize('grade', GRADE_LEVEL)
def test_real_python_solutions_and_wrong_answers(grade):
    for seed in range(5):
        items = build_items('backend', grade, seed)
        result = score_attempt(items, {i['id']: SOLUTIONS[i['template_id']] for i in items})
        assert result['score'] == 100, result
        assert all(i['status'] == 'correct' for i in result['items'])
        assert score_attempt(items, {i['id']: 'def solve(*args):\n    return None' for i in items})['score'] == 0


def test_negative_window_and_disconnected_graph_detect_wrong_solutions():
    middle = build_items('backend', 'middle', 0)
    for item in middle:
        assert item['code']['examples'][0] == item['code']['tests'][0]
        assert 'tests' not in public_item(item)['code']


@pytest.mark.parametrize('grade', GRADE_LEVEL)
def test_api_starts_and_scores_three_tasks(client, db, grade):
    from app.models import TestAttempt
    h = register(client, f'hybrid-{grade}@test.ru')
    assert client.post('/api/candidate/survey', json=SURVEY, headers=h).status_code == 200
    r = client.post('/api/testing/attempts', json={'specialization': 'backend', 'target_grade': grade}, headers=h)
    assert r.status_code == 201, r.text
    assert len(r.json()['items']) == 3
    attempt = db.get(TestAttempt, r.json()['id'])
    answers = {i['id']: SOLUTIONS[i['template_id']] for i in attempt.items}
    r = client.post(f'/api/testing/attempts/{attempt.id}/submit', json={'answers': answers}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()['score'] == 100 and r.json()['passed']
    assert r.json()['decision']['grade_after'] == grade


def test_old_saved_questions_remain_gradable():
    item = {'id':'q1', 'template_id':'be.old.example', 'kind':'input', 'level':0,
            'weight':1, 'skill':'Python', 'text':'Сколько будет 2+2?', 'answer':'4', 'options':None, 'code':None}
    old = copy.deepcopy(item)
    assert score_attempt([item], {'q1': '4'})['score'] == 100
    assert item == old


def test_api_resumes_and_submits_old_ten_question_attempt(client, db):
    import random
    from app.models import TestAttempt
    from app.testing_bank import templates_for
    from tests.conftest import correct_answer
    h = register(client, 'legacy-hybrid@test.ru')
    client.post('/api/candidate/survey', json=SURVEY, headers=h)
    r = client.post('/api/testing/attempts', json={'specialization': 'backend', 'target_grade': 'middle'}, headers=h)
    attempt = db.get(TestAttempt, r.json()['id'])
    old_templates = templates_for('backend')[:10]
    saved = []
    for n, template in enumerate(old_templates, 1):
        v = template.make(random.Random(n))
        saved.append({'id':f'q{n}', 'template_id':template.id, 'level':template.level,
                      'weight':template.level+1, 'skill':template.skill, 'kind':template.kind,
                      'text':v['text'], 'options':v.get('options'), 'answer':v.get('answer'), 'code':v.get('code')})
    attempt.items = saved
    db.commit()
    r = client.get(f'/api/testing/attempts/{attempt.id}', headers=h)
    assert len(r.json()['items']) == 10
    answers = {i['id']: correct_answer(i) for i in saved}
    r = client.post(f'/api/testing/attempts/{attempt.id}/submit', json={'answers':answers}, headers=h)
    assert r.status_code == 200 and r.json()['score'] == 100
    assert len(db.get(TestAttempt, attempt.id).items) == 10
