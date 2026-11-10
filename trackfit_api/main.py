"""API inicial; rotas de fichas apenas para protótipo local protegido."""
from fastapi import FastAPI
from pydantic import BaseModel

from trackfit_api.workout_routes import router as workout_router
from trackfit_api.auth_routes import router as auth_router
from trackfit_api.ai_routes import router as ai_router

app = FastAPI(title="TrackFit API", version="0.2.0", description="Protótipo local do TrackFit")
app.include_router(workout_router)
app.include_router(auth_router)
app.include_router(ai_router)


class HealthResponse(BaseModel):
    status: str
    version: str


class CapabilityResponse(BaseModel):
    key: str
    status: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.2.0")


@app.get("/capabilities", response_model=list[CapabilityResponse])
def capabilities() -> list[CapabilityResponse]:
    """Não confundir protótipo de fichas com produto pronto."""
    return [
        CapabilityResponse(key="registro_local_treinos", status="legado_disponivel"),
        CapabilityResponse(key="api_fichas", status="prototipo_local"),
        CapabilityResponse(key="autenticacao", status="prototipo_local"),
        CapabilityResponse(key="cadastro_alunos", status="pendente"),
        CapabilityResponse(key="geracao_fichas_ia", status="prototipo_local"),
        CapabilityResponse(key="revisao_professor", status="prototipo_local"),
        CapabilityResponse(key="app_android", status="pendente"),
    ]
