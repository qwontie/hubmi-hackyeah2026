from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider

from dependencies.providers.db import DbProvider
from dependencies.providers.llm import LlmProvider

container = make_async_container(DbProvider(), LlmProvider(), FastapiProvider())
