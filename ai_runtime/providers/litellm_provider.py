from litellm import acompletion

from ai_runtime.providers.provider import BaseProvider

from .litellm_mapper import LiteLLMMapper
from .litellm_exception_mapper import LiteLLMExceptionMapper

from ai_runtime.models import (
    ChatRequest,
    ChatResponse,
    ProviderCapabilities,
)

class LiteLLMProvider(BaseProvider):

    @property
    def capabilities(self) -> ProviderCapabilities:

        return ProviderCapabilities(
            chat=True,
            streaming=True,
        )

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        self.validate_request(request)

        try:

            payload = LiteLLMMapper.to_request(request)

            response = await acompletion(
                **payload,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )

            return LiteLLMMapper.from_response(response)

        except Exception as ex:
            raise LiteLLMExceptionMapper.map(ex)

    async def stream(
        self,
        request: ChatRequest,
    ):
        raise NotImplementedError()

    async def list_models(self) -> list[str]:
        return []

