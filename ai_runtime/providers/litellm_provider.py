from litellm import acompletion, aembedding

from .provider import BaseProvider

from .litellm_mapper import LiteLLMMapper
from .litellm_exception_mapper import LiteLLMExceptionMapper

from ai_runtime.conversation import ChatRequest
from ai_runtime.conversation import ChatResponse

from collections.abc import AsyncIterator
from ai_runtime.streaming.event import StreamEvent

from .provider_info import ProviderInfo
from .sdk_info import SDKInfo
from .capabilities import ProviderCapabilities

from .litellm_stream_parser import LiteLLMStreamParser
from ai_runtime.providers.enums import ProviderType

# Default capability hints per provider type. These are *negotiated* at
# runtime: a provider may advertise broader support, but the runtime only
# forwards capability-gated request fields when the flag is True here.
_PROVIDER_CAPABILITIES = {
    ProviderType.OPENAI: ProviderCapabilities(
        tools=True,
        vision=True,
        structured_output=True,
        embeddings=True,
        image_generation=True,
        transcription=True,
    ),
    ProviderType.GROQ: ProviderCapabilities(
        tools=True,
        structured_output=True,
    ),
    ProviderType.ANTHROPIC: ProviderCapabilities(
        tools=True,
        vision=True,
        reasoning=True,
    ),
}

class LiteLLMProvider(BaseProvider):

    @property
    def info(self):

        return ProviderInfo(
            provider=self.config.provider,
            model=self.config.model,
            sdkInfo=SDKInfo(
                sdk="LiteLLM",
                version="1.75.0"
            ),
            capabilities = _PROVIDER_CAPABILITIES.get(
                self.config.provider,
                ProviderCapabilities(),
            )
        )

    def _retry_kwargs(self) -> dict:
        # LiteLLM honors `num_retries` for automatic backoff.
        if self.config.max_retries and self.config.max_retries > 0:
            return {"num_retries": self.config.max_retries}
        return {}

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        self.validate_request(request)

        try:

            payload = LiteLLMMapper.to_request(
                self.config,
                request,
                self.info.capabilities,
            )

            response = await acompletion(
                **payload,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                **self._retry_kwargs(),
            )

            return LiteLLMMapper.from_response(response)

        except Exception as ex:
            raise LiteLLMExceptionMapper.map(ex)

    async def stream(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[StreamEvent]:

        self.validate_request(request)

        payload = LiteLLMMapper.to_request(
            self.config,
            request,
            self.info.capabilities,
        )

        payload["stream"] = True

        parser = LiteLLMStreamParser()

        try:

            response = await acompletion(
                **payload,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                **self._retry_kwargs(),
            )

            async for chunk in response:

                for event in parser.parse(chunk):

                    yield event

        except Exception as ex:

            raise LiteLLMExceptionMapper.map(ex) from ex

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        if not self.info.capabilities.embeddings:
            raise NotImplementedError(
                f"Provider {self.config.provider.value} does not support embeddings."
            )

        try:
            embed_model = model or self.config.litellm_model
            response = await aembedding(
                model=embed_model,
                input=texts,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                **self._retry_kwargs(),
            )
            return [item["embedding"] for item in response["data"]]
        except Exception as ex:
            raise LiteLLMExceptionMapper.map(ex)

    async def list_models(self) -> list[str]:
        return []

