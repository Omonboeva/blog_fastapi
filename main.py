from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.routers import auth, users, posts, comments


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield



app = FastAPI(
    title="📰 Blog API",
    description="FastAPI + PostgreSQL + Alembic",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(posts.router, prefix=API_PREFIX)
app.include_router(comments.router, prefix=API_PREFIX)


@app.get("/", tags=["Health"])
async def root() -> dict:
    return {
        "status": "ok",
        "message": "Blog API ishlayapti! 🎉",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "healthy"}