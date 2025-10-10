# app/main.py
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

class Status(BaseModel):
    ok: bool
    service: str
    version: str
    timestamp_utc: str

class Pong(BaseModel):
    pong: bool
    latency_ms: int

logger = logging.getLogger("proj2")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.setLevel(logging.INFO)
    logger.info("Starting Project 2 service...")

    yield  

    logger.info("Shutting down Project 2 service...")

app = FastAPI(
    title="Project 2",
    version="1.0.0",
    description="SE Project 2 – FastAPI baseline with async and good defaults.",
    lifespan=lifespan,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/", response_model=Status, tags=["meta"])
async def root() -> Status:
    return Status(
        ok=True,
        service="proj2",
        version="1.0.0",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/healthz", response_model=Status, tags=["meta"])
async def healthz() -> Status:
    return Status(
        ok=True,
        service="proj2",
        version="1.0.0",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/ready", response_model=Status, tags=["meta"])
async def ready() -> Status:
    return Status(
        ok=True,
        service="proj2",
        version="1.0.0",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/v1/ping", response_model=Pong, tags=["demo"])
async def ping(simulated_ms: int = 50) -> Pong:
    start = asyncio.get_event_loop().time()
    await asyncio.sleep(simulated_ms / 1000)
    end = asyncio.get_event_loop().time()
    return Pong(pong=True, latency_ms=int((end - start) * 1000))
