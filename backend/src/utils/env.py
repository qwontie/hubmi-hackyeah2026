import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_AUTH_SECRET_LENGTH = 32
MIN_DB_PASSWORD_LENGTH = 16


def is_prod() -> bool:
    return os.getenv("RUN_ENVIRONMENT") == "prod"


class Section(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")


class LogSettings(Section):
    level: str = "INFO"
    level_external: str = "WARNING"
    show_time: bool = False
    console_width: int = 150


class DatabaseSettings(Section):
    host: str = "postgres"
    port: int = 5432
    user: str = "hubmi"
    password: SecretStr = SecretStr("hubmi")
    db_name: str = "hubmi"
    min_pool_size: int = 5
    max_pool_size: int = 20
    scripts_connection_url: str = "postgresql://hubmi:hubmi@localhost:5432/hubmi"

    @property
    def connection_url(self) -> str:
        if not is_prod():
            return self.scripts_connection_url
        password = self.password.get_secret_value()
        return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.db_name}"

    @property
    def async_connection_url(self) -> str:
        return self.connection_url.replace("postgresql://", "postgresql+asyncpg://", 1)


class ApiSettings(Section):
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8080
    workers: int = 1
    docs: bool = False


class AuthSettings(Section):
    secret: SecretStr = SecretStr("")
    cookie_name: str = "hubmi_session"
    session_hours: int = 12


class MailSettings(Section):
    resend_api_key: SecretStr = SecretStr("")
    sender: str = "HubMi <hubmi@kotikot.com>"
    reply_to: str | None = None
    staff_email: str | None = None
    staff_digest_seconds: int = 600
    timeout_seconds: float = 10.0
    public_url: str = "https://hubmi.qwontie.dev"


class LlmSettings(Section):
    model: str = "google-gla:gemini-2.5-flash"
    gemini_api_key: SecretStr = SecretStr("")


class Settings(BaseSettings):
    log: LogSettings = Field(default_factory=LogSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    mailer: MailSettings = Field(default_factory=MailSettings)

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=("../.env", ".env"),
        env_nested_delimiter="__",
        extra="ignore",
    )


env = Settings()


def validate_prod_settings() -> None:
    if not is_prod():
        return
    secret = env.auth.secret.get_secret_value()
    if len(secret) < MIN_AUTH_SECRET_LENGTH or secret.lower() in {
        "secret",
        "changeme",
        "hubmi",
    }:
        message = "AUTH__SECRET must be at least 32 characters in production"
        raise RuntimeError(message)
    password = env.db.password.get_secret_value()
    if (
        password == env.db.user == env.db.db_name
        or len(password) < MIN_DB_PASSWORD_LENGTH
    ):
        message = "Production database credentials must not use defaults"
        raise RuntimeError(message)
