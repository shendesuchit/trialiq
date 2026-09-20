"""FastAPI application entry point for TrialIQ."""

import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from trialiq.api.routes.query import router as query_router
from trialiq.api.routes.trials import router as trials_router
from trialiq.config.settings import get_cors_origins
from trialiq.graph.connection import Neo4jConnection
from trialiq.api.routes.lineage import router as lineage_router


logger = logging.getLogger(__name__)


app = FastAPI(
    title="TrialIQ API",
    version="0.1.0",
    description="Evidence-grounded clinical trial intelligence API.",
)

app.include_router(
    lineage_router,
    prefix="/api/v1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    trials_router,
    prefix="/api/v1",
)

app.include_router(
    query_router,
    prefix="/api/v1",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a lightweight process health response."""

    return {
        "status": "ok",
        "service": "trialiq-api",
    }


@app.get("/ready")
def readiness_check() -> dict[str, str]:
    """Confirm that the API can reach its required graph dependency."""

    connection: Neo4jConnection | None = None

    try:
        connection = Neo4jConnection()
        connection.verify_connectivity()
    except Exception as exc:
        logger.warning("TrialIQ readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j is unavailable.",
        ) from exc
    finally:
        if connection is not None:
            connection.close()

    return {
        "status": "ready",
        "service": "trialiq-api",
    }
