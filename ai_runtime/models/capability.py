from pydantic import BaseModel

class ProviderCapabilities(BaseModel):

    streaming: bool = False

    tools: bool = False

    vision: bool = False

    embeddings: bool = False

    reasoning: bool = False

    json_mode: bool = False

    image_generation: bool = False