from pydantic import BaseModel

from ai_runtime.models.enums import ProviderType
from .sdk_info import SDKInfo

from .capabilities import (
    ProviderCapabilities,
)

class ProviderInfo(BaseModel):

    provider: ProviderType

    model: str

    sdkInfo: SDKInfo

    capabilities: ProviderCapabilities