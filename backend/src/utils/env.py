import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    session_days: int = 30


class LlmSettings(Section):
    model: str = "google-gla:gemini-2.5-flash"
    gemini_api_key: SecretStr = SecretStr("")


class Settings(BaseSettings):
    log: LogSettings = Field(default_factory=LogSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=("../.env", ".env"),
        env_nested_delimiter="__",
        extra="ignore",
    )


env = Settings()
