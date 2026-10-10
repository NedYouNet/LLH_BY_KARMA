"""
Настройки приложения.

Все параметры читаются из переменных окружения или файла `.env`
(библиотека pydantic-settings делает это автоматически).
Так мы не храним пароли и секреты в коде, а для Docker/сервера
просто подставляем другие значения.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Общее ---
    app_name: str = "FSP Talent API"
    environment: str = "dev"  # dev | prod | test
    api_prefix: str = "/api"

    # --- База данных ---
    # Формат: postgresql+psycopg://ПОЛЬЗОВАТЕЛЬ:ПАРОЛЬ@ХОСТ:ПОРТ/ИМЯ_БД
    database_url: str = "postgresql+psycopg://fsp:fsp@localhost:5432/fsp"

    # --- JWT (токены авторизации) ---
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION-please-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "fsp-talent"
    access_token_minutes: int = 15  # короткий срок: украденный access-токен быстро «протухает»
    refresh_token_days: int = 14
    email_token_hours: int = 48

    # --- Шифрование персональных данных (см. app/core/crypto.py) ---
    # "k1:<base64 32 байта>[,k0:<старый ключ>]". Сгенерировать: python -m scripts.encryption gen-key
    data_encryption_keys: str = ""

    # --- Защита от перебора и спама ---
    rate_limit_enabled: bool = True
    trust_proxy_headers: bool = False  # True, только если перед бэкендом стоит свой nginx/Caddy
    login_rate_per_ip_per_minute: int = 20
    login_max_failures: int = 5  # неудачных входов на один email...
    login_lockout_minutes: int = 15  # ...после этого вход блокируется на 15 минут
    register_rate_per_ip_per_hour: int = 20
    resend_rate_per_email_per_hour: int = 3

    # --- Регистрация и почта ---
    # True = нельзя войти, пока не подтвердил email (как требует ТЗ).
    email_verification_required: bool = True
    frontend_url: str = "http://localhost:5173"
    backend_public_url: str = "http://localhost:8000"
    smtp_host: str | None = None  # None = письма пишутся в лог (удобно при разработке)
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "FSP Talent <noreply@fsp-talent.local>"

    # --- Реестр ФСП ---
    # Файл с реальными результатами соревнований (xlsx или csv). Шаблон: python -m scripts.fsp_data template
    fsp_data_path: str = "data/fsp_results.xlsx"
    # Если ID нет в файле — искать в демо-реестре (заглушке). В бою, с настоящим API ФСП, выключить.
    fsp_demo_fallback: bool = True

    # --- Вход через FSP ID (OpenID Connect, как у Keycloak) ---
    # mock — встроенная имитация Keycloak-реалма ФСП (боевых доступов организаторы не дают);
    # oidc — настоящий провайдер: достаточно указать FSP_ID_ISSUER, CLIENT_ID и CLIENT_SECRET;
    # off  — кнопка «Войти через FSP ID» скрыта.
    fsp_id_mode: str = "mock"
    fsp_id_issuer: str = ""          # для oidc: https://<keycloak>/realms/<realm>
    fsp_id_client_id: str = "fsp-talent"
    fsp_id_client_secret: str = "dev-fsp-id-client-secret-change-me"

    # --- Микросервис ML (участник 3) ---
    ml_service_url: str | None = None  # ML внутри бэкенда (app/ml). Адрес — только если ML вынесен в отдельный сервис
    ml_timeout_seconds: float = 20.0

    # --- CORS: с каких адресов фронтенд может обращаться к API ---
    cors_origins: str = "*"  # через запятую: "http://localhost:5173,https://fsp.example.ru"

    # --- Правила тестирования ---
    grade_change_cooldown_days: int = 90  # грейд можно менять не чаще раза в 90 дней
    test_retry_cooldown_hours: int = 24  # пересдача на тот же грейд — не чаще раза в сутки
    test_pass_threshold: float = 70.0  # % для прохождения
    test_upgrade_hint_threshold: float = 90.0  # % при котором советуем попробовать грейд выше
    test_duration_minutes: int = 30
    test_questions_count: int = 10
    code_exec_timeout_seconds: float = 3.0

    # --- Веса ранжирования (сумма не обязана быть 1 — нормализуем в коде) ---
    # Подобраны на синтетической валидации (scripts/evaluate.py), см. документацию.
    # Кандидат без пройденного теста виден с пометкой «не подтверждён», но ниже: балл × 0.6
    rank_unverified_multiplier: float = 0.6
    rank_w_test: float = 0.35
    rank_w_fsp: float = 0.15
    rank_w_skills: float = 0.35
    rank_w_text: float = 0.05
    rank_w_activity: float = 0.10
    rank_adjacent_grade_multiplier: float = 0.7  # кандидат на грейд выше/ниже нужного

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Один объект настроек на всё приложение (кэшируется)."""
    return Settings()


settings = get_settings()


INSECURE_JWT_DEFAULTS = {"CHANGE-ME-IN-PRODUCTION-please-use-long-random-string",
                         "dev-secret-change-me-for-production-0123456789"}


def check_production_settings(s: Settings) -> list[str]:
    """
    Проверка перед запуском в продакшене. Если что-то небезопасно — сервер НЕ стартует
    (лучше упасть при запуске, чем работать с дефолтным секретом).
    """
    problems = []
    if s.environment != "prod":
        return problems
    if s.jwt_secret in INSECURE_JWT_DEFAULTS or len(s.jwt_secret) < 32:
        problems.append("JWT_SECRET дефолтный или короче 32 символов")
    if not s.data_encryption_keys:
        problems.append("Не задан DATA_ENCRYPTION_KEYS")
    if "*" in s.cors_origin_list:
        problems.append("CORS_ORIGINS='*' — укажите адрес фронтенда")
    if s.fsp_id_mode == "oidc" and (not s.fsp_id_issuer or s.fsp_id_client_secret.startswith("dev-")):
        problems.append("FSP_ID_MODE=oidc: задайте FSP_ID_ISSUER и FSP_ID_CLIENT_SECRET")
    return problems
