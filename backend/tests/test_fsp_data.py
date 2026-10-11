"""Реальные результаты ФСП из таблицы: чтение, проверка, приоритет над демо-реестром."""
import os
import time

import pytest
from openpyxl import Workbook

from app.services import fsp_service
from app.services.fsp_data import COLUMNS, load_dataset
from app.services.fsp_service import CombinedFspRegistry, FileFspRegistry, MockFspRegistry
from tests.conftest import ready_candidate, register


def write_xlsx(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Данные"
    ws.append(COLUMNS)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


ROWS = [
    # fsp_id, event, discipline, level, year, place, result, team, sport_rank, source_url, comment
    ["777001", "Чемпионат России", "Продуктовое программирование", "Всероссийский", 2024, "2 место", "", "Байт",
     "кмс", "https://example.ru/p1", ""],
    ["777001", "Региональный этап", "Продуктовое программирование", "региональный", 2025, 1, "", "", "", "", ""],
    ["777002", "", "", "", "", "", "", "", "", "", ""],                                   # участник без достижений
    ["", "Кубок", "", "всероссийский", 2024, "", "", "", "", "", ""],                      # нет ID
    ["777003", "Кубок", "", "галактический", 1999, "пятое", "", "", "", "ftp://x", ""],    # всё плохо
    ["777004", "Кубок", "", "всероссийский", 2024, "", "", "", "", "", "пример — удалить"],  # строка из шаблона
    ["777005", "Кубок", "", "всероссийский", 2024, "", "", "", "гроссмейстер", "", ""],     # неизвестный разряд
]

def test_load_dataset_parses_and_reports_errors_with_row_numbers(tmp_path):
    ds = load_dataset(write_xlsx(tmp_path / "f.xlsx", ROWS))
    assert set(ds.participants) == {"777001", "777002"}
    assert ds.participants["777002"] == []
    first, second = ds.participants["777001"]
    assert first["year"] == 2025 and first["place"] == 1 and first["result"] == "1 место"  # свежие — первыми
    assert second["level"] == "all_russian" and second["place"] == 2 and second["team"] == "Байт"
    assert second["verification_status"] == "verified" and second["source_url"] == "https://example.ru/p1"
    assert [e.split(":")[0] for e in ds.errors] == ["Строка 5", "Строка 6", "Строка 7", "Строка 8"]
    assert ds.ranks == {"777001": "КМС"} and "разряд" in ds.errors[3]
    bad = ds.errors[1]
    assert "уровень" in bad and "год" in bad and "место" in bad and "source_url" in bad
    assert "пример" in ds.errors[2]


def test_csv_from_russian_excel(tmp_path):
    """Excel в русской Windows сохраняет CSV в cp1251 и с разделителем «;»."""
    text = ";".join(COLUMNS) + "\n777010;Кубок России;;Международный;2023;3;;;МС;;\n"
    path = tmp_path / "f.csv"
    path.write_bytes(text.encode("cp1251"))
    ds = load_dataset(path)
    assert not ds.errors
    assert ds.participants["777010"][0]["level_name"] == "Международный" and ds.ranks["777010"] == "МС"


def test_file_registry_rereads_changed_file(tmp_path):
    path = write_xlsx(tmp_path / "f.xlsx", ROWS[:1])
    reg = FileFspRegistry(path)
    assert len(reg.get_participant("777001")["achievements"]) == 1
    write_xlsx(path, ROWS[:2])
    os.utime(path, (time.time() + 5, time.time() + 5))  # гарантируем новое время изменения
    assert len(reg.get_participant("777001")["achievements"]) == 2
    assert FileFspRegistry(tmp_path / "нет-такого.xlsx").get_participant("777001") is None


@pytest.fixture()
def real_registry(tmp_path, monkeypatch):
    def use(fallback: bool):
        reg = CombinedFspRegistry(FileFspRegistry(write_xlsx(tmp_path / "f.xlsx", ROWS)),
                                  MockFspRegistry() if fallback else None)
        monkeypatch.setattr(fsp_service, "registry", reg)
        return reg
    return use


def test_real_results_are_verified_for_employer(client, db, real_registry):
    real_registry(fallback=True)
    h = ready_candidate(client, db)
    assert client.post("/api/candidate/fsp", json={"fsp_id": "777001"}, headers=h).status_code == 200
    cid = client.get("/api/auth/me", headers=h).json()["candidate_profile_id"]
    he = register(client, "hr@test.ru", role="employer")
    card = client.get(f"/api/candidates/{cid}", headers=he).json()
    assert card["has_fsp"] is True and card["fsp_verification"] == "verified" and card["fsp_rank"] == "КМС"
    reg = client.get("/api/fsp/registry/777001").json()
    assert reg["source"] == "fsp_results_table" and reg["fsp_score"] > 0
    # ID, которого нет в таблице, берётся из демо-реестра с честной пометкой
    assert client.get("/api/fsp/registry/123457").json()["achievements"][0]["verification_status"] == "demo"


def test_participant_without_achievements_and_no_demo_fallback(client, db, real_registry):
    real_registry(fallback=False)
    h = ready_candidate(client, db)
    r = client.post("/api/candidate/fsp", json={"fsp_id": "123457"}, headers=h)  # есть только в демо
    assert r.status_code == 404 and r.json()["code"] == "FSP_NOT_FOUND"
    assert client.post("/api/candidate/fsp", json={"fsp_id": "777002"}, headers=h).status_code == 200
    cid = client.get("/api/auth/me", headers=h).json()["candidate_profile_id"]
    he = register(client, "hr@test.ru", role="employer")
    card = client.get(f"/api/candidates/{cid}", headers=he).json()
    assert card["has_fsp"] is False and card["fsp_verification"] == "none"  # без истории — не ошибка


def test_sync_updates_already_linked_profiles(client, db, engine, real_registry, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    import app.core.database as database
    from app.models import CandidateProfile
    from scripts.fsp_data import sync

    real_registry(fallback=True)
    h = ready_candidate(client, db)
    client.post("/api/candidate/fsp", json={"fsp_id": "777001"}, headers=h)
    c = db.query(CandidateProfile).filter_by(fsp_id="777001").one()
    c.fsp_achievements, c.fsp_score = [], 0.0  # как будто привязал до появления данных
    db.commit()
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    assert sync() == 0
    db.expire_all()
    c = db.query(CandidateProfile).filter_by(fsp_id="777001").one()
    assert len(c.fsp_achievements) == 2 and c.fsp_score > 0
