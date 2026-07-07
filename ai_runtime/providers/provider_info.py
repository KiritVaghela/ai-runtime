from pydantic import BaseModel

from .enums import ProviderType
from .sdk_info import SDKInfo

from .capabilities import (
    ProviderCapabilities,
)

class ProviderInfo(BaseModel):

    provider: ProviderType

    model: str

    sdkInfo: SDKInfo

    capabilities: ProviderCapabilities