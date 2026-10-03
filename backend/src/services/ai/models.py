import time
from functools import cache

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

from utils.env import env

from .costs import ensure_budget, log_ai_call


class AiUnavailableError(RuntimeError):
    pass


@cache
def google_provider() -> GoogleProvider:
    return GoogleProvider(api_key=env.llm.gemini_api_key.get_secret_value())


def chat_model_name() -> str:
    return env.llm.model.split(":", 1)[-1]


@cache
def chat_model() -> GoogleModel:
    return GoogleModel(
        chat_model_name(),
        provider=google_provider(),
        settings=GoogleModelSettings(
            temperature=0.2, google_thinking_config={"thinking_budget": 0}
        ),
    )


async def run_agent[T](agent: Agent[None, T], prompt: str, *, kind: str) -> T:
    await ensure_budget()
    started = time.perf_counter()
    try:
        result = await agent.run(prompt, model=chat_model())
    except Exception as e:
        await log_ai_call(
            kind=kind,
            model=chat_model_name(),
            input_tokens=0,
            output_tokens=0,
            latency_ms=int((time.perf_counter() - started) * 1000),
            ok=False,
            error=repr(e),
        )
        raise AiUnavailableError from e
    usage = result.usage
    await log_ai_call(
        kind=kind,
        model=chat_model_name(),
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        latency_ms=int((time.perf_counter() - started) * 1000),
        ok=True,
    )
    return result.output
