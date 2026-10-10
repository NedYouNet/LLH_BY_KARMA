"""Подборка кандидатов для работодателя: поиск по категориям, карточка кандидата, избранное."""
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.models import EmployerNeed, EmployerProfile, ShortlistItem, Vacancy
from app.reference import GRADE_CODES, GRADE_LEVEL, category_label
from app.repositories.repos import CandidateRepository, InvitationRepository, NeedRepository, ShortlistRepository
from app.schemas.candidate import CandidateDetail
from app.schemas.matching import CategoryBucket, NeedIn, NeedOut, SearchIn, SearchOut, ShortlistIn, ShortlistOut
from app.services.matching_engine import SearchCriteria, rank, score_candidate
from app.services.presenters import (candidate_card, candidate_detail, contact_basis, contact_basis_map,
                                     log_contact_access)


def criteria_from_need(n: EmployerNeed) -> SearchCriteria:
    """Сохранённая потребность -> критерии (нужный грейд + соседние, со штрафом за несовпадение)."""
    lvl = GRADE_LEVEL[n.grade]
    grades = [g for g in GRADE_CODES if abs(GRADE_LEVEL[g] - lvl) <= 1]
    return SearchCriteria(specialization=n.specialization, grades=grades, target_grade=n.grade,
                          skills=n.stack or [], text=" ".join(filter(None, [n.title, n.description])))


def criteria_from_vacancy(v: Vacancy, include_adjacent: bool = True) -> SearchCriteria:
    """Потребность работодателя (вакансия) -> критерии подборки."""
    lvl = GRADE_LEVEL[v.grade]
    grades = [g for g in GRADE_CODES if abs(GRADE_LEVEL[g] - lvl) <= (1 if include_adjacent else 0)]
    text = " ".join(filter(None, [v.title, v.description, v.team_description]))
    return SearchCriteria(specialization=v.specialization, grades=grades, target_grade=v.grade, skills=v.skills or [],
                          text=text, work_format=v.work_format if v.work_format == "office" else None,
                          city=v.city if v.work_format == "office" else None)


class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.candidates = CandidateRepository(db)

    def search(self, employer: EmployerProfile, req: SearchIn) -> SearchOut:
        crit = SearchCriteria(specialization=req.specialization, grades=list(req.grades), skills=req.skills,
                              text=req.text, fsp_only=req.fsp_only, only_verified=req.only_verified,
                              min_test_score=req.min_test_score,
                              work_format=req.work_format, city=req.city,
                              target_grade=req.grades[0] if len(req.grades) == 1 else None)
        return self._run(employer, crit, req.page, req.size)

    def search_query(self, employer: EmployerProfile, *, needs_id: int | None, specialization: str | None,
                     grades: list[str], stack: list[str], only_fsp: bool, min_test_score: float | None,
                     text: str | None, page: int, page_size: int, only_verified: bool = False) -> SearchOut:
        """
        GET /api/candidates. Если передан needs_id — берём критерии из сохранённой потребности,
        а явно переданные фильтры их уточняют (сама потребность при этом не меняется).
        """
        crit = criteria_from_need(self.get_need(employer, needs_id)) if needs_id else SearchCriteria()
        if specialization:
            crit.specialization = specialization
        if grades:
            crit.grades = list(grades)
            crit.target_grade = grades[0] if len(grades) == 1 else crit.target_grade
        if stack:
            crit.skills = stack
        if text:
            crit.text = text
        crit.fsp_only = only_fsp
        crit.only_verified = only_verified
        crit.min_test_score = min_test_score
        return self._run(employer, crit, page, page_size)

    # ----------------------------- потребности -----------------------------
    def list_needs(self, employer: EmployerProfile) -> list[NeedOut]:
        return [NeedOut.model_validate(n, from_attributes=True) for n in NeedRepository(self.db).by_employer(employer.id)]

    def get_need(self, employer: EmployerProfile, need_id: int) -> EmployerNeed:
        n = NeedRepository(self.db).get(need_id)
        if not n or n.employer_id != employer.id:
            raise NotFound("Потребность не найдена")
        return n

    def create_need(self, employer: EmployerProfile, data: NeedIn) -> NeedOut:
        n = NeedRepository(self.db).add(EmployerNeed(employer_id=employer.id, **data.model_dump()))
        self.db.commit()
        return NeedOut.model_validate(n, from_attributes=True)

    def update_need(self, employer: EmployerProfile, need_id: int, data: NeedIn) -> NeedOut:
        n = self.get_need(employer, need_id)
        for k, v in data.model_dump().items():
            setattr(n, k, v)
        self.db.commit()
        self.db.refresh(n)
        return NeedOut.model_validate(n, from_attributes=True)

    def delete_need(self, employer: EmployerProfile, need_id: int) -> None:
        self.db.delete(self.get_need(employer, need_id))
        self.db.commit()

    def for_vacancy(self, employer: EmployerProfile, v: Vacancy, page: int, size: int) -> SearchOut:
        return self._run(employer, criteria_from_vacancy(v), page, size)

    def _run(self, employer: EmployerProfile, crit: SearchCriteria, page: int, size: int) -> SearchOut:
        pool = self.candidates.searchable(crit.specialization, crit.grades or None, crit.only_verified)
        ranked = rank(pool, crit)

        # Блоки категорий («Бэкенд · Middle — 34»), считаем по отфильтрованной выдаче
        buckets: dict[tuple, list] = defaultdict(list)
        for c, _ in ranked:
            buckets[(c.effective_specialization, c.effective_grade)].append(c)
        categories = []
        for (s, g), lst in buckets.items():
            ver = [c for c in lst if c.grade_verified]
            categories.append(CategoryBucket(
                specialization=s, grade=g, category=category_label(s, g), count=len(lst), verified=len(ver),
                unverified=len(lst) - len(ver), with_fsp=sum(1 for c in lst if c.fsp_achievements),
                avg_test_score=round(sum(c.test_score or 0 for c in ver) / len(ver), 1) if ver else 0.0))
        categories.sort(key=lambda b: (b.specialization, GRADE_LEVEL[b.grade]))

        page_items = ranked[(page - 1) * size: page * size]
        ids = [c.id for c, _ in page_items]
        inv_status = InvitationRepository(self.db).latest_status_map(employer.id, ids)
        shortlisted = ShortlistRepository(self.db).ids_for_employer(employer.id)
        bases = contact_basis_map(self.db, employer.id, ids)
        items = [candidate_card(c, basis=bases.get(c.id), match=m,
                                invitation_status=inv_status.get(c.id), in_shortlist=c.id in shortlisted)
                 for c, m in page_items]
        return SearchOut(total=len(ranked), page=page, size=size, categories=categories, items=items)

    def categories_overview(self) -> list[CategoryBucket]:
        out = []
        for spec, grade, cnt, verified, with_fsp, avg in self.candidates.category_stats():
            out.append(CategoryBucket(specialization=spec, grade=grade, category=category_label(spec, grade),
                                      count=cnt, verified=int(verified or 0), unverified=cnt - int(verified or 0),
                                      with_fsp=int(with_fsp or 0), avg_test_score=round(float(avg or 0), 1)))
        return sorted(out, key=lambda b: (b.specialization, GRADE_LEVEL.get(b.grade, 0)))

    def candidate_for_employer(self, employer: EmployerProfile, candidate_id: int,
                               vacancy: Vacancy | None = None) -> CandidateDetail:
        """
        GET /api/candidates/{id} для работодателя.
        Контакты отдаются только при наличии основания (см. presenters.contact_basis),
        каждый такой просмотр пишется в журнал (152-ФЗ).
        """
        c = self.candidates.get(candidate_id)
        basis = contact_basis(self.db, employer.id, candidate_id) if c else None
        # Невидимых кандидатов (нет согласия/категории) показываем только тем, у кого есть основание
        if not c or (not c.is_searchable and basis is None):
            raise NotFound("Кандидат не найден")
        crit = criteria_from_vacancy(vacancy) if vacancy else SearchCriteria(target_grade=None)
        match = score_candidate(c, crit)
        if basis:
            log_contact_access(self.db, employer.id, c.id, basis)
            self.db.commit()
        status = InvitationRepository(self.db).latest_status_map(employer.id, [c.id]).get(c.id)
        in_sl = ShortlistRepository(self.db).find(employer.id, c.id) is not None
        return candidate_detail(c, basis=basis, match=match, invitation_status=status, in_shortlist=in_sl)

    # ----------------------------- избранное -----------------------------
    def shortlist(self, employer: EmployerProfile) -> list[ShortlistOut]:
        out = []
        for item in ShortlistRepository(self.db).for_employer(employer.id):
            c = self.candidates.get(item.candidate_id)
            out.append(ShortlistOut(id=item.id, note=item.note, vacancy_id=item.vacancy_id, created_at=item.created_at,
                                    candidate=candidate_card(c, basis=contact_basis(self.db, employer.id, c.id),
                                                             in_shortlist=True)))
        return out

    def add_to_shortlist(self, employer: EmployerProfile, data: ShortlistIn) -> ShortlistOut:
        repo = ShortlistRepository(self.db)
        c = self.candidates.get(data.candidate_id)
        if not c or not c.is_searchable:
            raise NotFound("Кандидат не найден")
        if repo.find(employer.id, c.id):
            raise Conflict("Кандидат уже в избранном", "ALREADY_SHORTLISTED")
        item = repo.add(ShortlistItem(employer_id=employer.id, candidate_id=c.id, vacancy_id=data.vacancy_id,
                                      note=data.note))
        self.db.commit()
        return ShortlistOut(id=item.id, note=item.note, vacancy_id=item.vacancy_id, created_at=item.created_at,
                            candidate=candidate_card(c, basis=contact_basis(self.db, employer.id, c.id), in_shortlist=True))

    def remove_from_shortlist(self, employer: EmployerProfile, candidate_id: int) -> None:
        repo = ShortlistRepository(self.db)
        item = repo.find(employer.id, candidate_id)
        if not item:
            raise NotFound("Кандидата нет в избранном")
        repo.delete(item)
        self.db.commit()
