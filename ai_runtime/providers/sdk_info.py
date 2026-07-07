from pydantic import BaseModel

class SDKInfo(BaseModel):
        
    sdk: str

    version: str