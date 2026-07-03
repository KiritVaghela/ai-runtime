from pydantic import BaseModel
from .capability import ProviderCapabilities

class ProviderInfo(BaseModel):

    name: str

    model: str

    capabilities: ProviderCapabilities