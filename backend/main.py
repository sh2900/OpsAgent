
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MongoDB when the API starts
    db.init_db()

    yield


app = FastAPI(
    title="OpsAgent",
    lifespan=lifespan
)


# Allow frontend communication during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
