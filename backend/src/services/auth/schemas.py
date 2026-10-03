import re
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, Field

from utils.db.models import AdminUser

LOGIN_RE = re.compile(r"^[a-z0-9][a-z0-9._@-]{0,63}$")


def _login(value: str) -> str:
    value = value.strip().lower()
    if not LOGIN_RE.fullmatch(value):
        message = "Login: lowercase letters, digits, . _ @ -"
        raise ValueError(message)
    return value


Login = Annotated[str, AfterValidator(_login)]
Password = Annotated[str, Field(min_length=8, max_length=200)]


class LoginBody(BaseModel):
    login: str
    password: str


class Me(BaseModel):
    login: str

    @classmethod
    def of(cls, admin: AdminUser) -> Self:
        return cls(login=admin.login)
