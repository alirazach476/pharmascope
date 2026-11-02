"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pharmascope import __disclaimer__, __version__
from pharmascope.api.routes import analytics, catalog, health, medicines, reports
from pharmascope.config.logging_config import setup_logging
from pharmascope.config.settings import get_settings

setup_logging()
settings = get_settings()

app = FastAPI(
    title="PharmaScope API",
    version=__version__,
    description=(
        "Pharmaceutical data intelligence API. "
        + __disclaimer__
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(medicines.router)
app.include_router(analytics.router)
app.include_router(reports.router)
app.include_router(catalog.router)
