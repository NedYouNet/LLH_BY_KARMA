"""
Нагрузочная проверка: «стабильная работа при одновременном использовании десятками пользователей».

Запускать на поднятом стенде с демо-данными (docker compose up + seed):

    python -m scripts.load_test                       # 50 пользователей, 30 секунд, http://localhost:8000
    python -m scripts.load_test --users 100 --seconds 60 --url http://localhost:8000

Каждый виртуальный пользователь в цикле делает то, что делают люди на платформе:
  работодатель — подборка под вакансию, поиск по категории, карточка кандидата;
  кандидат     — свой профиль, приглашения, список вакансий.
Итог — сколько запросов в секунду выдержал сервер, сколько было ошибок и время ответа
(медиана, 95-й и 99-й перцентили) по каждой операции. Результат пишется в scripts/output/load_test.md.
"""
import argparse
import asyncio
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

import httpx

PASSWORD = "demo12345"
EMPLOYERS = ["employer@demo.ru"] + [f"hr{i}@demo.ru" for i in range(1, 5)]
CANDIDATES = [f"cand{i}@demo.ru" for i in range(1, 16)]  # вместе с работодателями — 20 входов (лимит 20/мин с IP)


async def login(client: httpx.AsyncClient, email: str) -> dict | None:
    r = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    if r.status_code != 200:
        print(f"  не удалось войти как {email}: {r.status_code} {r.text[:100]}")
        return None
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def employer_user(client, headers, ctx, stats, stop_at):
    vacancies = ctx["vacancies"][headers["Authorization"]] or [None]
    while time.perf_counter() < stop_at:
        vid = random.choice(vacancies)
        if vid:
            await call(client, "GET", f"/api/vacancies/{vid}/matches", "Подборка под вакансию", headers, stats, ctx)
        spec = random.choice(["backend", "frontend", "data_science", "qa", "devops"])
        await call(client, "GET", "/api/candidates", "Поиск по категории", headers, stats, ctx,
                   params={"specialization": spec})
        if ctx["candidate_ids"]:
            cid = random.choice(ctx["candidate_ids"])
            await call(client, "GET", f"/api/candidates/{cid}", "Открыть профиль кандидата", headers, stats, ctx)


async def candidate_user(client, headers, ctx, stats, stop_at):
    while time.perf_counter() < stop_at:
        await call(client, "GET", "/api/candidate/profile", "Свой профиль", headers, stats, ctx)
        await call(client, "GET", "/api/invitations", "Мои приглашения", headers, stats, ctx)
        await call(client, "GET", "/api/vacancies", "Список вакансий", headers, stats, ctx)


async def call(client, method, url, name, headers, stats, ctx, params=None):
    t = time.perf_counter()
    try:
        r = await client.request(method, url, headers=headers, params=params)
        ok = r.status_code < 400
        if not ok:
            ctx.setdefault("errors", defaultdict(int))[f"{name}: {r.status_code}"] += 1
        if name == "Поиск по категории" and ok and not ctx["candidate_ids"]:
            ctx["candidate_ids"] = [c["id"] for c in r.json()["items"]]
    except httpx.HTTPError:
        ok = False
    stats[name].append(((time.perf_counter() - t) * 1000, ok))


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


async def main(url: str, users: int, seconds: int) -> str:
    limits = httpx.Limits(max_connections=users + 10, max_keepalive_connections=users + 10)
    async with httpx.AsyncClient(base_url=url, timeout=30, limits=limits) as client:
        print(f"Вход демо-пользователей на {url} ...")
        emp = [h for h in await asyncio.gather(*(login(client, e) for e in EMPLOYERS)) if h]
        cand = [h for h in await asyncio.gather(*(login(client, c) for c in CANDIDATES)) if h]
        if not emp or not cand:
            raise SystemExit("Нет входа: запущен ли стенд и залиты ли демо-данные (scripts.seed)?")
        ctx = {"vacancies": {}, "candidate_ids": []}
        for h in emp:  # у каждой компании — свои вакансии (чужие подборки закрыты: 404)
            ctx["vacancies"][h["Authorization"]] = [v["id"] for v in (await client.get("/api/vacancies/mine",
                                                                                        headers=h)).json()]
        stats: dict[str, list] = defaultdict(list)
        print(f"Нагрузка: {users} одновременных пользователей, {seconds} с ...")
        start = time.perf_counter()
        stop_at = start + seconds
        tasks = []
        for i in range(users):
            if i % 2 == 0:
                tasks.append(employer_user(client, emp[i % len(emp)], ctx, stats, stop_at))
            else:
                tasks.append(candidate_user(client, cand[i % len(cand)], ctx, stats, stop_at))
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

    total = sum(len(v) for v in stats.values())
    errors = sum(1 for v in stats.values() for _, ok in v if not ok)
    lines = [f"# Нагрузочная проверка\n",
             f"- Стенд: `{url}`; одновременных пользователей: **{users}**; длительность: {seconds} с",
             f"- Всего запросов: **{total}**, в секунду: **{total / elapsed:.0f}**, ошибок: **{errors}** "
             f"({100 * errors / max(total, 1):.2f}%)\n",
             "| Операция | Запросов | Медиана, мс | 95%, мс | 99%, мс |", "|---|---:|---:|---:|---:|"]
    for name, vals in stats.items():
        ms = [m for m, _ in vals]
        lines.append(f"| {name} | {len(ms)} | {statistics.median(ms):.0f} | {pct(ms, 95):.0f} | {pct(ms, 99):.0f} |")
    if ctx.get("errors"):
        lines.append("\nОшибки: " + ", ".join(f"{k} — {v}" for k, v in ctx["errors"].items()))
    report = "\n".join(lines) + "\n"
    out = Path(__file__).parent / "output"
    out.mkdir(exist_ok=True)
    (out / "load_test.md").write_text(report, encoding="utf-8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--users", type=int, default=50)
    ap.add_argument("--seconds", type=int, default=30)
    args = ap.parse_args()
    print(asyncio.run(main(args.url, args.users, args.seconds)))
