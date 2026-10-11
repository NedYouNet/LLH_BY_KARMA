from datetime import timedelta

import pytest

from app.core.database import utcnow
from app.models import TestAttempt
from scripts.verify_hybrid_testing import SOLUTIONS
from tests.conftest import SURVEY, register


def start(client, db, email='checks@test.ru', grade='middle'):
    h = register(client, email)
    client.post('/api/candidate/survey', json=SURVEY, headers=h)
    r = client.post('/api/testing/attempts', json={'specialization':'backend', 'target_grade':grade}, headers=h)
    assert r.status_code == 201
    a = db.get(TestAttempt, r.json()['id'])
    return h, a, a.items[0]


def check(client, headers, attempt, item, code):
    return client.post(f'/api/testing/attempts/{attempt.id}/check', headers=headers,
                       json={'item_id':item['id'], 'code':code})


@pytest.mark.parametrize('grade', ['intern','junior','middle','senior'])
def test_real_checks_do_not_complete_attempt_and_persist_counter(client, db, grade):
    h, a, item = start(client, db, grade=grade)
    r = check(client, h, a, item, SOLUTIONS[item['template_id']])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['passed'] == body['total'] == len(item['code']['tests'])
    assert body['checks_used'] == 1 and body['checks_remaining'] == 9
    assert set(body) == {'item_id','passed','total','checks_used','check_limit','checks_remaining','messages'}
    db.expire_all()
    saved = db.get(TestAttempt, a.id)
    assert saved.status == 'in_progress' and saved.score is None and saved.answers == {}
    r = client.get(f'/api/testing/attempts/{a.id}', headers=h)
    code = r.json()['items'][0]['code']
    assert code['checks_used'] == 1 and code['check_limit'] == 10
    assert 'tests' not in code


def test_ten_checks_per_item_then_final_submission_still_allowed(client, db):
    h, a, item = start(client, db)
    for used in range(1, 11):
        r = check(client, h, a, item, SOLUTIONS[item['template_id']])
        assert r.status_code == 200 and r.json()['checks_used'] == used
    r = check(client, h, a, item, SOLUTIONS[item['template_id']])
    assert r.status_code == 409 and r.json()['code'] == 'CHECK_LIMIT_REACHED'
    assert r.json()['checks_used'] == 10
    other = a.items[1]
    assert check(client, h, a, other, SOLUTIONS[other['template_id']]).json()['checks_used'] == 1
    answers = {i['id']: SOLUTIONS[i['template_id']] for i in a.items}
    r = client.post(f'/api/testing/attempts/{a.id}/submit', headers=h, json={'answers':answers})
    assert r.status_code == 200 and r.json()['score'] == 100
    r = check(client, h, a, item, SOLUTIONS[item['template_id']])
    assert r.status_code == 409 and r.json()['code'] == 'ATTEMPT_FINISHED'


def test_wrong_syntax_and_forbidden_import_consume_checks(client, db):
    h, a, item = start(client, db)
    for used, code in enumerate(['def solve(*args):\n    return None', 'def solve(:', 'import os\ndef solve(*args):\n    return 0'], 1):
        r = check(client, h, a, item, code)
        assert r.status_code == 200 and r.json()['passed'] == 0
        assert r.json()['checks_used'] == used and r.json()['messages']


def test_hidden_errors_are_not_exposed(client, db, monkeypatch):
    h, a, item = start(client, db)
    monkeypatch.setattr('app.services.testing_service.run_tests', lambda *args: {
        'passed':0, 'total':12, 'violations':[], 'errors':['hidden expected answer: 123456789']})
    r = check(client, h, a, item, 'def solve(*args):\n    return 0')
    assert r.status_code == 200 and '123456789' not in r.text


def test_invalid_checks_do_not_consume_limit(client, db):
    h, a, item = start(client, db)
    assert check(client, h, a, item, '   ').status_code == 400
    assert check(client, h, a, item, 'x'*10001).status_code == 422
    assert check(client, h, a, {'id':'unknown'}, 'def solve(): pass').status_code == 404
    db.expire_all()
    assert db.get(TestAttempt, a.id).items[0].get('checks_used',0) == 0


def test_other_candidate_cannot_check_attempt(client, db):
    h, a, item = start(client, db)
    other = register(client, 'other-check@test.ru')
    assert check(client, other, a, item, SOLUTIONS[item['template_id']]).status_code == 404
    employer = register(client, 'employer-check@test.ru', role='employer')
    assert check(client, employer, a, item, SOLUTIONS[item['template_id']]).status_code == 403
    assert check(client, {}, a, item, SOLUTIONS[item['template_id']]).status_code == 401


def test_expired_attempt_cannot_be_checked(client, db):
    h, a, item = start(client, db)
    a.deadline_at = utcnow()-timedelta(seconds=1)
    db.commit()
    r = check(client, h, a, item, SOLUTIONS[item['template_id']])
    assert r.status_code == 409 and r.json()['code'] == 'ATTEMPT_EXPIRED'


def test_old_attempt_checks_start_at_zero(client, db):
    h, a, item = start(client, db)
    assert 'checks_used' not in item
    r = client.get(f'/api/testing/attempts/{a.id}', headers=h)
    assert r.json()['items'][0]['code']['checks_used'] == 0


def test_non_code_item_cannot_be_checked(client, db):
    h, a, item = start(client, db)
    a.items = [{**item,'kind':'input','code':None,'answer':'4'}]
    db.commit()
    r = check(client, h, a, item, 'def solve(): pass')
    assert r.status_code == 400 and r.json()['code'] == 'NOT_CODE_ITEM'
