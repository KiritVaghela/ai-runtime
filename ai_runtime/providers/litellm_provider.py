from litellm import acompletion

from ai_runtime.providers.provider import BaseProvider

from ai_runtime.providers.litellm_mapper import LiteLLMMapper
from ai_runtime.providers.litellm_exception_mapper import LiteLLMExceptionMapper

from ai_runtime.models import (
    ChatRequest,
    ChatResponse,
    ProviderCapabilities,
)


from ai_runtime.providers.litellm_stream_parser import LiteLLMStreamParser
from collections.abc import AsyncIterator
from ai_runtime.streaming.event import StreamEvent

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

            payload = LiteLLMMapper.to_request(self.config, request)

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
    ) -> AsyncIterator[StreamEvent]:

        self.validate_request(request)

        payload = LiteLLMMapper.to_request(self.config, request)

        payload["stream"] = True

        parser = LiteLLMStreamParser()

        try:

            response = await acompletion(
                **payload,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )

            async for chunk in response:

                for event in parser.parse(chunk):

                    yield event

        except Exception as ex:

            raise LiteLLMExceptionMapper.map(ex) from ex
    
    

    async def list_models(self) -> list[str]:
        return []

