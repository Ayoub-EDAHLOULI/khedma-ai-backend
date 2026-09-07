from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exception_handlers import register_exception_handlers
from app.routers import applications, jobs, matches, profile, search, voice

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(matches.router)
app.include_router(applications.router)
app.include_router(search.router)
app.include_router(voice.router)


@app.get("/health")
def health():
    return {"status": "ok"}
