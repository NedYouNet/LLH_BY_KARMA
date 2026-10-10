from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class ORMModel(BaseModel):
    """База для схем, которые читаются из моделей SQLAlchemy."""
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    total: int = Field(description="Всего записей (для пагинации)")
    items: list[T]


class Message(BaseModel):
    message: str


class SalaryRange(BaseModel):
    """Вилка ЗП в рублях — обязательна и в вакансии, и в приглашении (правило ТЗ №1)."""
    salary_from: int = Field(gt=0, le=10_000_000, description="ЗП от, ₽ в месяц", examples=[200000])
    salary_to: int = Field(gt=0, le=10_000_000, description="ЗП до, ₽ в месяц", examples=[280000])
    salary_type: Literal["gross", "net"] = Field(
        "gross", description="gross — до вычета НДФЛ, net — «на руки». Подписываем явно, как просили организаторы")

    @field_validator("salary_to")
    @classmethod
    def check_range(cls, v, info):
        # field_validator (а не model_validator), чтобы ошибка 422 указывала на конкретное поле формы
        frm = info.data.get("salary_from")
        if frm is not None and v < frm:
            raise ValueError("Зарплата «до» не может быть меньше зарплаты «от»")
        return v


SALARY_TYPE_LABEL = {"gross": "до вычета НДФЛ", "net": "на руки"}


class Reason(BaseModel):
    """Плашка-обоснование для UI: почему кандидат в выдаче."""
    type: str = Field(description="test | skills | text | fsp | strengths | activity | grade")
    label: str = Field(examples=["Бэкенд · Middle: тест 87/100"])
    positive: bool = Field(description="True — подсвечивать зелёным")
    missing: list[str] | None = Field(default=None, description="Для type=skills: каких навыков не хватает")
