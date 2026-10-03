from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider

from dependencies.providers.db import DbProvider
from dependencies.providers.llm import LlmProvider
from dependencies.providers.mail import MailProvider

container = make_async_container(
    DbProvider(), LlmProvider(), MailProvider(), FastapiProvider()
)
