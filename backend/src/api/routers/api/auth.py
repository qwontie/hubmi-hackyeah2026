from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.security import StaffPerson
from services.auth.admins import AdminRepository
from services.auth.crypto import create_session
from services.auth.guard import LoginBlockedError, LoginGuard
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
        samesite="strict",
        max_age=env.auth.session_hours * 3600,
        path="/",
    )


@router.post("/login")
async def login(
    body: LoginBody,
    request: Request,
    response: Response,
    session: FromDishka[AsyncSession],
) -> Me:
    guard = LoginGuard(session)
    try:
        await guard.check(request, body.login)
    except LoginBlockedError as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many login attempts",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    admin = await AdminRepository(session).verify(body.login, body.password)
    if admin is None:
        await guard.failed(request, body.login)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong login or password")
    await guard.succeeded(request, body.login)
    set_session_cookie(request, response, create_session(admin.id, admin.token_version))
    return Me.of(admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    admin: StaffPerson,
    session: FromDishka[AsyncSession],
) -> None:
    admin.token_version += 1
    session.add(admin)
    await session.commit()
    response.delete_cookie(
        key=env.auth.cookie_name,
        path="/",
        httponly=True,
        secure=is_https(request),
        samesite="strict",
    )


@router.get("/me")
async def me(request: Request, response: Response, admin: StaffPerson) -> Me:
    set_session_cookie(request, response, create_session(admin.id, admin.token_version))
    return Me.of(admin)
