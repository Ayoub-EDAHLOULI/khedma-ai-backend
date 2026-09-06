from fastapi import FastAPI

from app.exception_handlers import register_exception_handlers
from app.routers import applications, jobs, matches, profile, search

app = FastAPI()

register_exception_handlers(app)

app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(matches.router)
app.include_router(applications.router)
app.include_router(search.router)


@app.get("/health")
def health():
    return {"status": "ok"}
