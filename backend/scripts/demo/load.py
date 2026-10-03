import argparse
import asyncio
import hashlib
import json
import secrets
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr
from rich.console import Console
from sqlalchemy import func, update
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dependencies.container import container
from scripts.demo import registry, timeline
from services.ai import AiUnavailableError, embed_queries
from services.ai.models import chat_model_name
from services.auth.admins import AdminRepository
from services.dialogue.service import author_message, reply, set_status
from services.dialogue.service import background as delivery_tasks
from services.kreator import Canvas
from services.kreator import repository as ideas
from services.mail import Mailer
from services.middleman import InstitutionType, UnclearRequestError, generate_plan
from services.middleman import repository as adaptations
from services.modules import published_innovation
from services.needs import (
    POWIATS,
    TextRejectedError,
    create_need,
    match_need,
    refresh_cluster_summary,
    update_need,
)
from services.needs.service import clean_text
from services.needs.tokens import new_token
from services.search import nearest_innovations
from services.tester import repository as tester
from utils.db import init_db, session_scope
from utils.db.models import (
    AdminAction,
    AdminUser,
    AiCall,
    FeedbackKind,
    Idea,
    IdeaStage,
    IdeaStatus,
    Innovation,
    MatchResult,
    Message,
    MessageDelivery,
    MessageDirection,
    Need,
    NeedCluster,
    NeedStatus,
    SignupStatus,
    TesterRole,
    TestSignup,
)
from utils.db.models.adaptation import Adaptation
from utils.db.models.feedback import Feedback
from utils.env import MailSettings
from utils.logging import setup_logging

console = Console()
HERE = Path(__file__).parent
ADMINS = ("anna.rops", "tomasz.rops")
ROPS = "rops"
VOTE_DELAY_HOURS = 0.4
CLOSE_DELAY_HOURS = 2.0
MODULE_SHARE = 10
BACKGROUND_TIMEOUT = 180


@dataclass(slots=True)
class Run:
    session: AsyncSession
    now: datetime
    admins: list[AdminUser]
    mailer: Mailer
    created: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def count(self, kind: str) -> None:
        self.created[kind] = self.created.get(kind, 0) + 1

    def warn(self, text: str) -> None:
        self.warnings.append(text)
        console.print(f"[yellow]skip[/] {text}")

    def admin_for(self, key: str) -> AdminUser:
        return self.admins[sum(key.encode()) % len(self.admins)]


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load demo needs, replies, votes, ideas and adaptations"
        " through the real services; every row is recorded in demo_record"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="load only the first N needs"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="run again although demo rows exist; adds only what is missing",
    )
    return parser.parse_args()


def read(name: str) -> dict[str, Any]:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


async def ensure_admins(session: AsyncSession) -> list[AdminUser]:
    repo = AdminRepository(session)
    result = []
    for login in ADMINS:
        admin = await repo.by_login(login)
        known = await registry.lookup(session, registry.ADMIN, login)
        if admin is not None and admin.id != known:
            msg = f"admin {login} exists and is not a demo row; refusing to touch it"
            raise SystemExit(msg)
        if admin is None:
            admin, _ = await repo.upsert(login, secrets.token_urlsafe(32))
            await registry.register(session, registry.ADMIN, login, admin.id)
        result.append(admin)
    return result


def thread_hours(item: dict[str, Any]) -> float:
    total = sum(m["after_hours"] for m in item.get("thread", []))
    return total + (CLOSE_DELAY_HOURS if item.get("close") else 0)


def plan_needs(
    data: dict[str, Any], limit: int | None, now: datetime
) -> list[tuple[datetime, dict[str, Any]]]:
    rising = set(data["rising_topics"])
    topics: dict[str, list[str]] = {}
    for item in data["needs"]:
        topics.setdefault(item["topic"], []).append(item["key"])
    ages: dict[str, float] = {}
    for topic, keys in topics.items():
        ages |= timeline.topic_ages(keys, rising=topic in rising)
    needs = data["needs"][:limit] if limit else data["needs"]
    planned = [
        (
            timeline.need_time(
                n["key"], ages[n["key"]], thread_hours=thread_hours(n), now=now
            ),
            n,
        )
        for n in needs
    ]
    return sorted(planned, key=lambda pair: pair[0])


async def backdate_need(session: AsyncSession, need: Need, moment: datetime) -> None:
    values: dict[str, Any] = {"created_at": moment, "updated_at": moment}
    if need.consent_at is not None:
        values["consent_at"] = moment
    await session.exec(update(Need).where(col(Need.id) == need.id).values(**values))
    await session.exec(
        update(MatchResult)
        .where(col(MatchResult.need_id) == need.id)
        .values(created_at=moment)
    )
    await session.commit()


async def top_title(session: AsyncSession, need: Need) -> str:
    title = (
        await session.exec(
            select(Innovation.title)
            .join(MatchResult, col(MatchResult.innovation_id) == col(Innovation.id))
            .where(col(MatchResult.need_id) == need.id)
            .order_by(col(MatchResult.rank))
        )
    ).first()
    if title is not None:
        return title
    nearest = await nearest_innovations(session, list(need.embedding or []), limit=1)
    return nearest[0][0].title if nearest else "z naszej biblioteki"


async def backdate_message(
    session: AsyncSession, message_id: uuid.UUID, moment: datetime
) -> None:
    await session.exec(
        update(Message)
        .where(col(Message.id) == message_id)
        .values(sent_at=moment, created_at=moment, updated_at=moment)
    )
    await session.exec(
        update(AdminAction)
        .where(col(AdminAction.details)["message_id"].astext == str(message_id))
        .values(created_at=moment)
    )
    await session.commit()


async def mark_read(
    session: AsyncSession, ids: list[uuid.UUID], moment: datetime
) -> None:
    if ids:
        await session.exec(
            update(Message).where(col(Message.id).in_(ids)).values(read_at=moment)
        )
        await session.commit()


async def play_thread(
    run: Run, owner: Need | Idea, key: str, start: datetime, item: dict[str, Any]
) -> datetime:
    moment = start
    unread: list[uuid.UUID] = []
    for index, step in enumerate(item.get("thread", [])):
        moment = timeline.after(moment, step["after_hours"], now=run.now)
        message_key = f"{key}:m{index}"
        if step["from"] == ROPS:
            moment = timeline.office(moment, message_key, now=run.now)
        if await registry.lookup(run.session, registry.MESSAGE, message_key):
            continue
        if step["from"] == ROPS:
            body = step["body"]
            if "{top}" in body and isinstance(owner, Need):
                body = body.replace("{top}", await top_title(run.session, owner))
            sent = await reply(run.session, owner, run.admin_for(key), body, run.mailer)
            await mark_read(run.session, unread, moment)
            unread = []
        else:
            sent = await author_message(run.session, owner, step["body"])
            unread.append(sent.id)
        await registry.register(run.session, registry.MESSAGE, message_key, sent.id)
        await backdate_message(run.session, sent.id, moment)
        run.count(registry.MESSAGE)
    return moment


async def close_need(run: Run, need: Need, key: str, moment: datetime) -> None:
    await run.session.refresh(need)
    if need.status == NeedStatus.CLOSED:
        return
    admin = run.admin_for(key)
    await set_status(run.session, need, admin, NeedStatus.CLOSED)
    await run.session.exec(
        update(AdminAction)
        .where(
            col(AdminAction.action) == "need.status",
            col(AdminAction.target_id) == str(need.id),
            col(AdminAction.admin_id) == admin.id,
        )
        .values(created_at=moment)
    )
    await run.session.commit()


async def load_need(
    run: Run, item: dict[str, Any], moment: datetime, vector: list[float]
) -> None:
    session = run.session
    key = item["key"]
    need_id = await registry.lookup(session, registry.NEED, key)
    if need_id is None:
        try:
            if item["origin"] == "form":
                outcome = await create_need(
                    session,
                    item["text"],
                    powiat=item["powiat"],
                    contact_email=item.get("email"),
                    vector=vector,
                )
            else:
                outcome = await match_need(
                    session, item["text"], powiat=item["powiat"], vector=vector
                )
        except TextRejectedError as e:
            run.warn(f"need {key}: {e.code}")
            return
        need, token, cluster = outcome.need, outcome.token, outcome.cluster
        await registry.register(session, registry.NEED, key, need.id)
        run.count(registry.NEED)
        if cluster is not None and cluster.size == 1:
            await registry.register(
                session, registry.CLUSTER, str(cluster.id), cluster.id
            )
            run.count(registry.CLUSTER)
        if item["origin"] == "match" and (
            item.get("email") or item.get("nothing_fits")
        ):
            await update_need(
                session,
                need.id,
                token,
                contact_email=item.get("email"),
                nothing_fits=item.get("nothing_fits") or None,
            )
        await backdate_need(session, need, moment)
    else:
        found = await session.get(Need, need_id)
        if found is None:
            run.warn(f"need {key}: registered but missing")
            return
        need = found
    await session.refresh(need)
    last = await play_thread(run, need, key, need.created_at, item)
    if item.get("close"):
        last = timeline.after(last, CLOSE_DELAY_HOURS, now=run.now)
        await close_need(run, need, key, last)
    await session.exec(
        update(Need).where(col(Need.id) == need.id).values(updated_at=last)
    )
    await session.commit()


async def load_needs(run: Run, data: dict[str, Any], limit: int | None) -> None:
    planned = plan_needs(data, limit, run.now)
    missing = [
        (moment, item)
        for moment, item in planned
        if await registry.lookup(run.session, registry.NEED, item["key"]) is None
    ]
    texts = [clean_text(item["text"]) for _, item in missing]
    vectors = await embed_queries(texts, kind="embed_need") if texts else []
    by_key = {
        item["key"]: vector for (_, item), vector in zip(missing, vectors, strict=True)
    }
    for index, (moment, item) in enumerate(planned, start=1):
        console.print(
            f"[dim]{index:>3}/{len(planned)}[/] {item['key']} "
            f"{moment.astimezone(timeline.WARSAW):%d.%m %H:%M} {item['text'][:60]}"
        )
        try:
            await load_need(run, item, moment, by_key.get(item["key"], []))
        except AiUnavailableError:
            run.warn(f"need {item['key']}: model unavailable")


async def need_by_key(run: Run, key: str) -> Need | None:
    need_id = await registry.lookup(run.session, registry.NEED, key)
    return None if need_id is None else await run.session.get(Need, need_id)


async def backdate_feedback(
    session: AsyncSession, feedback_id: uuid.UUID, moment: datetime
) -> None:
    await session.exec(
        update(Feedback)
        .where(col(Feedback.id) == feedback_id)
        .values(created_at=moment, updated_at=moment)
    )
    await session.commit()


def demo_voter(key: str) -> str:
    return hashlib.sha256(f"demo-voter:{key}".encode()).hexdigest()


async def load_match_votes(run: Run, votes: list[dict[str, Any]]) -> None:
    for vote in votes:
        if await registry.lookup(run.session, registry.FEEDBACK, vote["key"]):
            continue
        need = await need_by_key(run, vote["need"])
        if need is None:
            continue
        innovation_id = (
            await run.session.exec(
                select(MatchResult.innovation_id).where(
                    col(MatchResult.need_id) == need.id,
                    col(MatchResult.rank) == vote["rank"],
                )
            )
        ).first()
        if innovation_id is None:
            run.warn(
                f"vote {vote['key']}: need {vote['need']} has no rank {vote['rank']}"
            )
            continue
        feedback = await tester.add_vote(
            run.session,
            innovation_id=innovation_id,
            kind=FeedbackKind(vote["kind"]),
            need_id=need.id,
            voter_hash=demo_voter(vote["key"]),
            comment=vote.get("comment"),
        )
        await registry.register(
            run.session, registry.FEEDBACK, vote["key"], feedback.id
        )
        await backdate_feedback(
            run.session,
            feedback.id,
            timeline.after(need.created_at, VOTE_DELAY_HOURS, now=run.now),
        )
        run.count(registry.FEEDBACK)


async def innovation(run: Run, slug: str) -> Innovation | None:
    found = await published_innovation(run.session, slug)
    if found is None:
        run.warn(f"innovation {slug} is not published")
    return found


async def load_innovation_votes(run: Run, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        target = await innovation(run, entry["slug"])
        if target is None:
            continue
        kinds = ["fits"] * entry["fits"] + ["does_not_fit"] * entry["does_not_fit"]
        comments = {
            kind: [c["text"] for c in entry["comments"] if c["kind"] == kind]
            for kind in ("fits", "does_not_fit")
        }
        moments = timeline.spread(entry["slug"], len(kinds), now=run.now)
        for index, (kind, moment) in enumerate(zip(kinds, moments, strict=True)):
            key = f"{entry['slug']}:{index}"
            if await registry.lookup(run.session, registry.FEEDBACK, key):
                continue
            comment = comments[kind].pop(0) if comments[kind] else None
            feedback = await tester.add_vote(
                run.session,
                innovation_id=target.id,
                kind=FeedbackKind(kind),
                need_id=None,
                voter_hash=demo_voter(key),
                comment=comment,
            )
            await registry.register(run.session, registry.FEEDBACK, key, feedback.id)
            await backdate_feedback(run.session, feedback.id, moment)
            run.count(registry.FEEDBACK)


async def load_improvements(run: Run, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        if await registry.lookup(run.session, registry.FEEDBACK, entry["key"]):
            continue
        target = await innovation(run, entry["slug"])
        if target is None:
            continue
        feedback = await tester.add_improvement(
            run.session, innovation_id=target.id, text_=entry["text"]
        )
        await registry.register(
            run.session, registry.FEEDBACK, entry["key"], feedback.id
        )
        await backdate_feedback(
            run.session,
            feedback.id,
            timeline.days_ago(entry["key"], entry["days_ago"], now=run.now),
        )
        run.count(registry.FEEDBACK)


async def load_signups(run: Run, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        if await registry.lookup(run.session, registry.SIGNUP, entry["key"]):
            continue
        target = await innovation(run, entry["slug"])
        if target is None:
            continue
        signup = await tester.add_signup(
            run.session,
            innovation_id=target.id,
            who=TesterRole(entry["who"]),
            organization=entry["organization"],
            powiat=entry["powiat"],
            contact_email=entry["email"],
            note=entry["note"] or "",
        )
        await registry.register(run.session, registry.SIGNUP, entry["key"], signup.id)
        status = SignupStatus(entry["status"])
        if status != SignupStatus.NEW:
            await tester.set_signup_status(run.session, signup.id, status)
        moment = timeline.days_ago(entry["key"], entry["days_ago"], now=run.now)
        await run.session.exec(
            update(TestSignup)
            .where(col(TestSignup.id) == signup.id)
            .values(created_at=moment, consent_at=moment, updated_at=moment)
        )
        await run.session.commit()
        run.count(registry.SIGNUP)


async def load_idea(run: Run, entry: dict[str, Any]) -> None:
    session = run.session
    key = entry["key"]
    idea_id = await registry.lookup(session, registry.IDEA, key)
    moment = timeline.days_ago(key, entry["days_ago"], now=run.now)
    if idea_id is None:
        _, token_hash = new_token()
        problem = await need_by_key(run, entry.get("problem_need", ""))
        idea = await ideas.create(
            session,
            title=entry["title"],
            essence=entry["essence"],
            for_whom=entry["for_whom"],
            stage=IdeaStage(entry["stage"]),
            canvas=Canvas.model_validate(entry["canvas"]),
            powiat=entry["powiat"],
            contact_email=entry["email"],
            token_hash=token_hash,
            problem_id=problem.cluster_id if problem else None,
        )
        await registry.register(session, registry.IDEA, key, idea.id)
        run.count(registry.IDEA)
        status = IdeaStatus(entry["status"])
        if status != IdeaStatus.NEW:
            idea.status = status
            idea = await ideas.save(session, idea, reembed=False)
        values: dict[str, Any] = {"created_at": moment, "updated_at": moment}
        if idea.consent_at is not None:
            values["consent_at"] = moment
        await session.exec(update(Idea).where(col(Idea.id) == idea.id).values(**values))
        await session.commit()
    else:
        found = await session.get(Idea, idea_id)
        if found is None:
            run.warn(f"idea {key}: registered but missing")
            return
        idea = found
    await session.refresh(idea)
    await play_thread(run, idea, key, idea.created_at, entry)


async def load_adaptation(run: Run, entry: dict[str, Any]) -> None:
    session = run.session
    if await registry.lookup(session, registry.ADAPTATION, entry["key"]):
        return
    target = await innovation(run, entry["slug"])
    if target is None:
        return
    candidates = await adaptations.candidates(session, target)
    await session.commit()
    kind = InstitutionType(entry["institution_type"])
    try:
        plan = await generate_plan(
            innovation=target,
            institution=kind,
            place=entry["place"],
            powiat_name=POWIATS.get(entry["powiat"]),
            context=entry["context"],
            candidates=candidates,
        )
    except (UnclearRequestError, AiUnavailableError) as e:
        run.warn(f"adaptation {entry['key']}: {type(e).__name__}")
        return
    stored = await adaptations.store(
        session,
        innovation=target,
        institution_type=kind,
        place=entry["place"],
        powiat=entry["powiat"],
        context=entry["context"],
        plan=plan,
        model=chat_model_name(),
    )
    await registry.register(session, registry.ADAPTATION, entry["key"], stored.id)
    moment = timeline.days_ago(entry["key"], entry["days_ago"], now=run.now)
    await session.exec(
        update(Adaptation)
        .where(col(Adaptation.id) == stored.id)
        .values(created_at=moment)
    )
    await session.commit()
    run.count(registry.ADAPTATION)


async def wait_background() -> None:
    current = asyncio.current_task()
    pending = {t for t in asyncio.all_tasks() if t is not current} | delivery_tasks
    if pending:
        await asyncio.wait(pending, timeout=BACKGROUND_TIMEOUT)


async def finish_clusters(run: Run) -> None:
    session = run.session
    touched = list(
        (
            await session.exec(
                select(Need.cluster_id)
                .where(
                    col(Need.id).in_(await registry.row_ids(session, registry.NEED)),
                    col(Need.cluster_id).is_not(None),
                )
                .distinct()
            )
        ).all()
    )
    demo_clusters = set(await registry.row_ids(session, registry.CLUSTER))
    for cluster_id in touched:
        if cluster_id is None:
            continue
        cluster = await session.get(NeedCluster, cluster_id)
        if cluster is None:
            continue
        if (
            cluster.summary_stale
            or cluster.summary_size != cluster.size
            or not cluster.summary
        ):
            await session.commit()
            await refresh_cluster_summary(cluster_id)
        bounds = (
            await session.exec(
                select(func.min(Need.created_at), func.max(Need.created_at)).where(
                    col(Need.cluster_id) == cluster_id
                )
            )
        ).one()
        values: dict[str, Any] = {"last_need_at": bounds[1]}
        if cluster_id in demo_clusters:
            values["created_at"] = bounds[0]
        await session.exec(
            update(NeedCluster)
            .where(col(NeedCluster.id) == cluster_id)
            .values(**values)
        )
        await session.commit()


async def report(run: Run, started: datetime) -> None:
    session = run.session
    console.print("\n[bold]demo rows[/]")
    for kind, total in (await registry.counts(session)).items():
        console.print(f"  {kind:<14} {total:>4}  (+{run.created.get(kind, 0)} now)")
    rows = await session.exec(
        select(AiCall.kind, func.count(), func.sum(AiCall.cost_usd))
        .where(col(AiCall.created_at) >= started)
        .group_by(col(AiCall.kind))
    )
    total = 0.0
    console.print("\n[bold]model calls during this run[/]")
    for kind, calls, cost in rows.all():
        total += float(cost or 0)
        console.print(f"  {kind:<18} {calls:>4} calls  ${float(cost or 0):.4f}")
    console.print(f"  [bold]total ${total:.4f}[/]")
    pending = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            col(Message.id).in_(await registry.row_ids(session, registry.MESSAGE)),
            col(Message.direction) == MessageDirection.TO_AUTHOR,
            col(Message.delivery_status) == MessageDelivery.PENDING,
        )
    )
    if pending:
        console.print(f"[red]{pending} demo replies still pending delivery[/]")
    for warning in run.warnings:
        console.print(f"[yellow]warning[/] {warning}")


async def run(args: argparse.Namespace) -> int:
    setup_logging()
    started = datetime.now(UTC) - timedelta(seconds=1)
    needs = read("needs.json")
    modules = read("modules.json")
    share = max(1, args.limit // MODULE_SHARE) if args.limit else None
    try:
        await init_db()
        async with session_scope() as session, httpx.AsyncClient() as client:
            existing = sum((await registry.counts(session)).values())
            if existing and not args.force:
                console.print(
                    f"[red]demo data is already loaded ({existing} rows).[/] "
                    "Run demo.wipe first, or pass --force to add only what is missing."
                )
                return 1
            state = Run(
                session=session,
                now=datetime.now(UTC),
                admins=await ensure_admins(session),
                mailer=Mailer(MailSettings(resend_api_key=SecretStr("")), client),
            )
            await load_needs(state, needs, args.limit)
            await load_match_votes(state, modules["match_votes"])
            await load_innovation_votes(state, modules["innovation_votes"][:share])
            await load_improvements(state, modules["improvements"][:share])
            await load_signups(state, modules["test_signups"][:share])
            for entry in modules["ideas"][:share]:
                await load_idea(state, entry)
            for entry in modules["adaptations"][:share]:
                await load_adaptation(state, entry)
            await wait_background()
            await finish_clusters(state)
            await wait_background()
            await report(state, started)
    finally:
        await container.close()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse())))


if __name__ == "__main__":
    main()
