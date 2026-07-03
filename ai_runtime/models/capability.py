from pydantic import BaseModel, ConfigDict


class ProviderCapabilities(BaseModel):

    model_config = ConfigDict(frozen=True)

    chat: bool = True

    streaming: bool = False

    tools: bool = False

    vision: bool = False

    embeddings: bool = False

    reasoning: bool = False

    image_generation: bool = False