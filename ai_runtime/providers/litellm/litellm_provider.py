from litellm import acompletion

from ai_runtime.providers.provider import BaseProvider

from .mapper import LiteLLMMapper
from .exception_mapper import LiteLLMExceptionMapper


class LiteLLMProvider(BaseProvider):

    async def chat(self, request):

        try:

            payload = LiteLLMMapper.to_request(
                request
            )

            response = await acompletion(
                **payload,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )

            return LiteLLMMapper.from_response(
                response
            )

        except Exception as ex:
            raise LiteLLMExceptionMapper.map(ex)