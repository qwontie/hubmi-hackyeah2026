import asyncio
import contextlib
from collections.abc import AsyncGenerator

import httpx
from dishka import Provider, Scope, provide

from services.dialogue.links import inbox_url
from services.mail import Mailer, StaffNotifier
from services.mail.watch import watch
from utils.env import env


class MailProvider(Provider):
    @provide(scope=Scope.APP)
    async def client(self) -> AsyncGenerator[httpx.AsyncClient]:
        async with httpx.AsyncClient() as client:
            yield client

    @provide(scope=Scope.APP)
    def mailer(self, client: httpx.AsyncClient) -> Mailer:
        return Mailer(env.mailer, client)

    @provide(scope=Scope.APP)
    async def staff(self, mailer: Mailer) -> AsyncGenerator[StaffNotifier]:
        notifier = StaffNotifier(mailer, env.mailer, inbox_url())
        task = asyncio.create_task(watch(notifier))
        try:
            yield notifier
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await notifier.close()
