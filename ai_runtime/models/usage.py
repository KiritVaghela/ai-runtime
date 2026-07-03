from pydantic import BaseModel

class Usage(BaseModel):

    prompt_tokens: int = 0

    completion_tokens: int = 0

    total_tokens: int = 0