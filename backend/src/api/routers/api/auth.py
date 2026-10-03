from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.security import AdminPerson
from services.auth.admins import AdminRepository
from services.auth.crypto import create_session
from services.auth.schemas import LoginBody, Me
from utils.env import env

router = APIRouter(route_class=DishkaRoute)


def is_https(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return proto.split(",")[0].strip() == "https"


def set_session_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        key=env.auth.cookie_name,
        value=token,
        httponly=True,
        secure=is_https(request),
        samesite="lax",
        max_age=env.auth.session_days * 24 * 3600,
        path="/",
    )


@router.post("/login")
async def login(
    body: LoginBody,
    request: Request,
    response: Response,
    session: FromDishka[AsyncSession],
) -> Me:
    admin = await AdminRepository(session).verify(body.login, body.password)
    if admin is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong login or password")
    set_session_cookie(request, response, create_session(admin.id))
    return Me.of(admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(key=env.auth.cookie_name, path="/")


@router.get("/me")
async def me(admin: AdminPerson) -> Me:
    return Me.of(admin)
