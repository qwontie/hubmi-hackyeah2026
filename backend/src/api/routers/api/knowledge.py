import uuid
from typing import Annotated, Any, Literal
from urllib.parse import quote

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field, HttpUrl
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import conflict, invalid, not_found
from api.limits import rate_limit
from api.security import AdminPerson, admin_from_secret, current_admin
from services.ai.costs import use_budget_scope
from services.bus import bus
from services.dialogue.audit import record
from services.knowledge import (
    KnowledgeImportRunningError,
    MaterialFilters,
    adding,
    get_material,
    latest_runs,
    list_materials,
    run_payload,
    start_knowledge_import,
)
from services.knowledge.editing import (
    ChallengePatch,
    MaterialPatch,
    patch_challenge,
    patch_material,
)
from services.knowledge.map import (
    AdminMap,
    PublicMap,
    admin_map,
    geojson_bytes,
    geojson_etag,
    public_map,
)
from services.knowledge.materials import topic_counts
from services.knowledge.queries import (
    ChallengeFilters,
    area_counts,
    challenge_detail,
    find_challenge,
    kind_counts,
    list_challenges,
    material_detail,
)
from services.knowledge.schemas import (
    AdminChallenge,
    AdminMaterial,
    ChallengeDetail,
    ChallengeSummary,
    CountedRef,
    MaterialDetail,
    MaterialSummary,
    Page,
    kind_refs,
)
from services.knowledge.topics import AREAS, TOPICS
from utils.db.models import AdminRole, MaterialFile
from utils.db.models.import_run import ImportTrigger
from utils.db.models.material import KnowledgeStatus, MaterialKind
from utils.env import env

router = APIRouter(route_class=DishkaRoute, tags=["knowledge"])
admin_router = APIRouter(
    route_class=DishkaRoute, tags=["admin"], dependencies=[Depends(current_admin)]
)
limiter = rate_limit("knowledge", per_minute=120)

NO_MATERIAL = "Nie znaleziono takiego materiału."
NO_CHALLENGE = "Nie znaleziono takiego wyzwania."
RUNNING = "Aktualizacja zasobów już trwa. Poczekaj na jej zakończenie."

PageNumber = Annotated[int, Query(ge=1, le=1000)]
PerPage = Annotated[int, Query(ge=1, le=100)]
SearchText = Annotated[str | None, Query(min_length=2, max_length=200)]
Key = Annotated[str, Path(min_length=1, max_length=120)]
add_limit = rate_limit("material_add", per_minute=10, per_day=200)
TOO_BIG = "Plik jest za duży. Limit to 30 MB."
NOT_PDF = "Dodaj plik PDF."
NO_JOB = "Nie znaleziono tego zadania."
NO_FILE = "Ten materiał nie ma pliku w HubMi."
BAD_CHARS = "Tekst zawiera niedozwolone znaki."
Year = Annotated[int, Field(ge=1990, le=2100)]


class MaterialLinkBody(BaseModel):
    kind: Literal["url"]
    url: HttpUrl
    title: Annotated[str, Field(max_length=200)] | None = None
    material_kind: MaterialKind = MaterialKind.PUBLICATION
    year: Year | None = None


class MaterialTextBody(BaseModel):
    kind: Literal["text"]
    title: Annotated[str, Field(min_length=3, max_length=200)]
    text: Annotated[str, Field(min_length=400, max_length=adding.MAX_TEXT_CHARS)]
    material_kind: MaterialKind = MaterialKind.PUBLICATION
    year: Year | None = None


class JobStarted(BaseModel):
    job_id: str


def _accepted(
    admin: AdminPerson, session: AsyncSession, source: adding.NewMaterial
) -> str:
    job_id = adding.start(source)
    record(
        session,
        admin,
        "material.add",
        target=("material_job", job_id),
        details={"kind": source.kind, "url": source.url, "filename": source.filename},
    )
    return job_id


def _topic(value: str | None) -> str | None:
    return value if value in TOPICS else None


def _area(value: str | None) -> str | None:
    return value if value in AREAS else None


@router.get("/materials", dependencies=[Depends(limiter)])
async def materials(  # noqa: PLR0913
    *,
    session: FromDishka[AsyncSession],
    kind: MaterialKind | None = None,
    topic: Annotated[str | None, Query(max_length=60)] = None,
    year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    q: SearchText = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[MaterialSummary]:
    if topic and _topic(topic) is None:
        return Page(items=[], total=0, page=page, per_page=per_page)
    filters = MaterialFilters(
        kind=kind, topic=topic, year=year, q=q.strip() if q else None
    )
    rows, total = await list_materials(session, filters, page=page, per_page=per_page)
    return Page(
        items=[MaterialSummary.build(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/materials/topics", dependencies=[Depends(limiter)])
async def material_topics(session: FromDishka[AsyncSession]) -> dict[str, Any]:
    counts = await topic_counts(session)
    return {
        "topics": [
            CountedRef(slug=slug, name=name, count=counts.get(slug, 0))
            for slug, name in TOPICS.items()
        ],
        "kinds": kind_refs(await kind_counts(session)),
    }


@router.get("/materials/{material_id}", dependencies=[Depends(limiter)])
async def material(
    material_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> MaterialDetail:
    found = await get_material(session, material_id)
    if found is None:
        raise not_found(NO_MATERIAL)
    return await material_detail(session, found)


@router.get(
    "/materials/{material_id}/file",
    response_class=Response,
    dependencies=[Depends(limiter)],
)
async def material_file(
    material_id: uuid.UUID, request: Request, session: FromDishka[AsyncSession]
) -> Response:
    found = await get_material(session, material_id, published_only=False)
    stored = await session.get(MaterialFile, material_id) if found else None
    if found is None or stored is None:
        raise not_found(NO_FILE)
    published = found.status == KnowledgeStatus.PUBLISHED
    if not published:
        viewer = await admin_from_secret(request.cookies.get(env.auth.cookie_name))
        if viewer is None or viewer.role != AdminRole.ADMIN:
            raise not_found(NO_FILE)
    headers = {
        "Cache-Control": "public, max-age=3600" if published else "private, no-store",
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(stored.filename)}",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=stored.data, media_type=stored.mime_type, headers=headers)


@router.get("/challenges", dependencies=[Depends(limiter)])
async def challenges(
    session: FromDishka[AsyncSession],
    area: Annotated[str | None, Query(max_length=60)] = None,
    q: SearchText = None,
    page: PageNumber = 1,
    per_page: PerPage = 50,
) -> Page[ChallengeSummary]:
    if area and _area(area) is None:
        return Page(items=[], total=0, page=page, per_page=per_page)
    rows, total = await list_challenges(
        session,
        ChallengeFilters(area=area, q=q.strip() if q else None),
        page=page,
        per_page=per_page,
    )
    return Page(
        items=[ChallengeSummary.build(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/challenges/areas", dependencies=[Depends(limiter)])
async def challenge_areas(session: FromDishka[AsyncSession]) -> list[CountedRef]:
    counts = await area_counts(session)
    return [
        CountedRef(slug=slug, name=name, count=counts.get(slug, 0))
        for slug, name in AREAS.items()
    ]


@router.get("/challenges/{key}", dependencies=[Depends(limiter)])
async def challenge(key: Key, session: FromDishka[AsyncSession]) -> ChallengeDetail:
    found = await find_challenge(session, key)
    if found is None:
        raise not_found(NO_CHALLENGE)
    return await challenge_detail(session, found)


@router.get("/map", dependencies=[Depends(limiter)])
async def map_data(session: FromDishka[AsyncSession]) -> PublicMap:
    return await public_map(session)


@router.get("/map/powiats.geojson", dependencies=[Depends(limiter)])
async def map_geojson(request: Request) -> Response:
    etag = f'"{geojson_etag()}"'
    headers = {"ETag": etag, "Cache-Control": "public, max-age=86400"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(geojson_bytes(), media_type="application/geo+json", headers=headers)


@admin_router.get("/map")
async def map_admin(
    session: FromDishka[AsyncSession], days: Annotated[int, Query(ge=1, le=365)] = 30
) -> AdminMap:
    return await admin_map(session, recent_days=days)


@admin_router.post("/knowledge/import/run", status_code=status.HTTP_202_ACCEPTED)
async def run_import(
    admin: AdminPerson, session: FromDishka[AsyncSession]
) -> dict[str, str]:
    try:
        with use_budget_scope("batch"):
            started = await start_knowledge_import(trigger=ImportTrigger.ADMIN)
    except KnowledgeImportRunningError as exc:
        raise conflict(RUNNING) from exc
    record(session, admin, "knowledge.import.run", target=("knowledge_run", started.id))
    await session.commit()
    return {"run_id": str(started.id)}


@admin_router.get("/knowledge/import/runs")
async def import_runs(
    session: FromDishka[AsyncSession], limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> list[dict[str, Any]]:
    return [run_payload(item) for item in await latest_runs(session, limit)]


@admin_router.get("/materials")
async def admin_materials(  # noqa: PLR0913
    *,
    session: FromDishka[AsyncSession],
    kind: MaterialKind | None = None,
    topic: Annotated[str | None, Query(max_length=60)] = None,
    status_: Annotated[KnowledgeStatus | None, Query(alias="status")] = None,
    edited: bool | None = None,
    q: SearchText = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[AdminMaterial]:
    filters = MaterialFilters(
        kind=kind,
        topic=topic,
        q=q.strip() if q else None,
        status=status_,
        edited=edited,
    )
    rows, total = await list_materials(session, filters, page=page, per_page=per_page)
    return Page(
        items=[AdminMaterial.build_admin(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@admin_router.post(
    "/materials",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(add_limit)],
)
async def add_material(
    body: Annotated[MaterialLinkBody | MaterialTextBody, Field(discriminator="kind")],
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> JobStarted:
    if isinstance(body, MaterialLinkBody):
        source = adding.NewMaterial(
            kind="url",
            url=str(body.url),
            title=body.title,
            material_kind=body.material_kind,
            year=body.year,
        )
    else:
        if "\x00" in body.text or "\x00" in body.title:
            error = invalid("text", BAD_CHARS)
            raise error
        source = adding.NewMaterial(
            kind="text",
            text=body.text,
            title=body.title,
            material_kind=body.material_kind,
            year=body.year,
        )
    job_id = _accepted(admin, session, source)
    await session.commit()
    return JobStarted(job_id=job_id)


@admin_router.post(
    "/materials/upload",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(add_limit)],
)
async def upload_material(  # noqa: PLR0913
    *,
    file: Annotated[UploadFile, File()],
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    title: Annotated[str | None, Form(max_length=200)] = None,
    material_kind: Annotated[MaterialKind, Form()] = MaterialKind.PUBLICATION,
    year: Annotated[int | None, Form(ge=1990, le=2100)] = None,
) -> JobStarted:
    data = await file.read(adding.MAX_PDF_BYTES + 1)
    if len(data) > adding.MAX_PDF_BYTES:
        error = invalid("file", TOO_BIG)
        raise error
    if not data.startswith(b"%PDF-"):
        error = invalid("file", NOT_PDF)
        raise error
    filename = (file.filename or "material.pdf").rsplit("/", 1)[-1][:120]
    source = adding.NewMaterial(
        kind="pdf",
        data=data,
        filename=filename,
        title=title,
        material_kind=material_kind,
        year=year,
    )
    job_id = _accepted(admin, session, source)
    await session.commit()
    return JobStarted(job_id=job_id)


@admin_router.get("/materials/jobs/{job_id}")
async def material_job(job_id: Annotated[str, Path(max_length=40)]) -> dict[str, Any]:
    found = adding.job(job_id)
    if found is None:
        raise not_found(NO_JOB)
    return found


@admin_router.get("/materials/{material_id}")
async def admin_material(
    material_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> AdminMaterial:
    found = await get_material(session, material_id, published_only=False)
    if found is None:
        raise not_found(NO_MATERIAL)
    return AdminMaterial.build_admin(found)


@admin_router.patch("/materials/{material_id}")
async def edit_material(
    material_id: uuid.UUID,
    patch: MaterialPatch,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminMaterial:
    found = await get_material(session, material_id, published_only=False)
    if found is None:
        raise not_found(NO_MATERIAL)
    changed = await patch_material(session, found, patch)
    out = AdminMaterial.build_admin(found)
    if changed:
        record(
            session,
            admin,
            "material.update",
            target=("material", found.id),
            details={"fields": changed},
        )
        await session.commit()
        bus.publish("material.updated", out.model_dump(mode="json"))
    return out


@admin_router.get("/challenges")
async def admin_challenges(  # noqa: PLR0913
    *,
    session: FromDishka[AsyncSession],
    area: Annotated[str | None, Query(max_length=60)] = None,
    status_: Annotated[KnowledgeStatus | None, Query(alias="status")] = None,
    verified: bool | None = None,
    q: SearchText = None,
    page: PageNumber = 1,
    per_page: PerPage = 50,
) -> Page[AdminChallenge]:
    rows, total = await list_challenges(
        session,
        ChallengeFilters(
            area=area, q=q.strip() if q else None, status=status_, verified=verified
        ),
        page=page,
        per_page=per_page,
    )
    return Page(
        items=[AdminChallenge.build_admin(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@admin_router.get("/challenges/{key}")
async def admin_challenge(
    key: Key, session: FromDishka[AsyncSession]
) -> AdminChallenge:
    found = await find_challenge(session, key, published_only=False)
    if found is None:
        raise not_found(NO_CHALLENGE)
    return AdminChallenge.build_admin(found)


@admin_router.patch("/challenges/{key}")
async def edit_challenge(
    key: Key,
    patch: ChallengePatch,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminChallenge:
    found = await find_challenge(session, key, published_only=False)
    if found is None:
        raise not_found(NO_CHALLENGE)
    changed = await patch_challenge(session, found, patch, admin)
    out = AdminChallenge.build_admin(found)
    if changed:
        record(
            session,
            admin,
            "challenge.update",
            target=("challenge", found.id),
            details={"fields": changed},
        )
        await session.commit()
        bus.publish("challenge.updated", out.model_dump(mode="json"))
    return out
