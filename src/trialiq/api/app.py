"""FastAPI application entry point for TrialIQ."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trialiq.api.routes.lineage import router as lineage_router
from trialiq.api.routes.query import router as query_router
from trialiq.api.routes.trials import router as trials_router
from trialiq.api.runtime_health import RuntimeReadiness, get_runtime_readiness
from trialiq.config.settings import get_cors_origins
from trialiq.llm.service import get_llm_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run the one-time LLM provider preflight at application startup."""
    try:
        status = get_llm_service().preflight()
        if status.healthy:
            logger.info(
                "TrialIQ LLM ready provider=%s model=%s",
                status.selected_provider,
                status.selected_model,
            )
        else:
            logger.warning("TrialIQ started without a usable LLM provider")
    except Exception:
        logger.exception("TrialIQ LLM startup preflight failed")
    yield


app = FastAPI(
    title="TrialIQ API",
    version="0.1.0",
    description="Evidence-grounded clinical trial intelligence API.",
    lifespan=lifespan,
)

app.include_router(lineage_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trials_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "trialiq-api"}


@app.get("/ready", response_model=RuntimeReadiness)
def readiness_check() -> RuntimeReadiness:
    """Return dependency-level readiness without hiding degraded subsystems."""
    return get_runtime_readiness()
