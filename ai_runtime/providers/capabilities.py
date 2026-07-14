from pydantic import BaseModel


class ProviderCapabilities(BaseModel):

    chat: bool = True

    streaming: bool = True

    tools: bool = False

    vision: bool = False

    structured_output: bool = False

    reasoning: bool = False

    embeddings: bool = False

    image_generation: bool = False

    transcription: bool = False