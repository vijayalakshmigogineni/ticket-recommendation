"""Internal debug/evaluation dashboard API. Pure HTTP glue over recommender/ --
no business logic lives here. No auth: trusted, local-only engineering tool.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.routers import customers, evaluation, feedback, interactions, run, search, system, tickets

app = FastAPI(title="RCM Recommender Debug Dashboard API")

_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_cors_origins = os.environ.get("DASHBOARD_CORS_ORIGINS")
allow_origins = _cors_origins.split(",") if _cors_origins else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(system.router)
app.include_router(customers.router)
app.include_router(tickets.router)
app.include_router(interactions.router)
app.include_router(run.router)
app.include_router(search.router)
app.include_router(evaluation.router)
app.include_router(feedback.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
