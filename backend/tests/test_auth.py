from tests.conftest import register


def test_register_and_login_requires_verified_email(client):
    r = client.post("/api/auth/register", json={"email": "a@test.ru", "password": "Secure2026x", "role": "candidate"})
    assert r.status_code == 201
    assert r.json()["verification_required"] is True

    r = client.post("/api/auth/login", json={"email": "a@test.ru", "password": "Secure2026x"})
    assert r.status_code == 403 and r.json()["code"] == "EMAIL_NOT_VERIFIED"


def test_duplicate_email_conflict(client):
    register(client, "dup@test.ru")
    r = client.post("/api/auth/register", json={"email": "DUP@test.ru", "password": "Secure2026x", "role": "candidate"})
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"


def test_wrong_password(client):
    register(client, "pw@test.ru")
    r = client.post("/api/auth/login", json={"email": "pw@test.ru", "password": "wrong-pass"})
    assert r.status_code == 401


def test_employer_can_register_without_company_but_cannot_invite(client, db):
    from tests.conftest import ready_candidate, register
    ready_candidate(client, db)
    he = register(client, "e@test.ru", role="employer", company_name="")
    cid = client.get("/api/candidates", headers=he).json()["items"][0]["id"]
    body = {"candidate_id": cid, "message": "Привет", "salary_from": 1, "salary_to": 2}
    r = client.post("/api/invitations", json=body, headers=he)
    assert r.status_code == 400 and r.json()["code"] == "COMPANY_PROFILE_INCOMPLETE"
    client.patch("/api/employer/profile", json={"company_name": "ООО Ромашка", "contact": "@hr_romashka"}, headers=he)
    inv = client.post("/api/invitations", json=body, headers=he).json()
    assert inv["contact_method"] == "@hr_romashka" and inv["company"]["company_name"] == "ООО Ромашка"


def test_registration_consent_and_short_survey(client):
    r = client.post("/api/auth/register", json={"email": "c2@test.ru", "password": "Secure2026x", "role": "candidate",
                                               "consent_processing": True})
    from tests.conftest import register  # noqa: F401
    token = r.json()["dev_verification_token"]
    client.post("/api/auth/verify-email", json={"token": token})
    t = client.post("/api/auth/login", json={"email": "c2@test.ru", "password": "Secure2026x"}).json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    client.patch("/api/candidate/profile", json={"skills": ["React", "Git"]}, headers=h)
    s = client.post("/api/candidate/survey", json={"industry": "it", "specialization": "frontend",
                                                    "declared_grade": "junior"}, headers=h)
    assert s.status_code == 200 and s.json()["skills"] == ["React", "Git"] and s.json()["consent_processing"] is True


def test_me_and_refresh(client):
    h = register(client, "me@test.ru")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["user"]["role"] == "candidate" and me["onboarding"]["survey_completed"] is False
    tokens = client.post("/api/auth/login", json={"email": "me@test.ru", "password": "Secure2026x"}).json()
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # access-токен нельзя использовать как refresh
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401


def test_no_token_and_role_guards(client):
    assert client.get("/api/candidate/profile").status_code == 401
    h = register(client, "c@test.ru")
    r = client.post("/api/candidates/search", json={}, headers=h)
    assert r.status_code == 403 and r.json()["code"] == "ROLE_REQUIRED"
    he = register(client, "emp@test.ru", role="employer")
    assert client.get("/api/candidate/profile", headers=he).status_code == 403
