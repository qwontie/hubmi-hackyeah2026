from dishka import Provider, Scope, provide
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

from utils.env import env


class LlmProvider(Provider):
    @provide(scope=Scope.APP)
    def agent(self) -> Agent:
        model = GoogleModel(
            env.llm.model.split(":", 1)[-1],
            provider=GoogleProvider(api_key=env.llm.gemini_api_key.get_secret_value()),
            settings=GoogleModelSettings(
                temperature=0.0, google_thinking_config={"thinking_budget": 0}
            ),
        )
        return Agent(model)
