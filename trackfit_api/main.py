"""API inicial: sem dados de alunos ou prescrições até haver autenticação."""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="TrackFit API", version="0.1.0", description="Base inicial do MVP TrackFit")


class HealthResponse(BaseModel):
    status: str
    version: str


class CapabilityResponse(BaseModel):
    key: str
    status: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/capabilities", response_model=list[CapabilityResponse])
def capabilities() -> list[CapabilityResponse]:
    """Transparência sobre o que já existe e o que ainda NÃO está disponível."""
    return [
        CapabilityResponse(key="registro_local_treinos", status="legado_disponivel"),
        CapabilityResponse(key="autenticacao", status="pendente"),
        CapabilityResponse(key="cadastro_alunos", status="pendente"),
        CapabilityResponse(key="geracao_fichas_ia", status="pendente"),
        CapabilityResponse(key="revisao_professor", status="pendente"),
        CapabilityResponse(key="app_android", status="pendente"),
    ]
