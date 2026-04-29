from pydantic import BaseModel

class GoogleToken(BaseModel):
    token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict
