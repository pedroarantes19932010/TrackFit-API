"""Login local e consulta de identidade. Cadastro é administrativo, não público."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from trackfit_api.identity import authenticate, current_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(payload: LoginInput):
    token = authenticate(payload.username, payload.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"access_token": token, "token_type": "bearer", "expires_in": 43200}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
