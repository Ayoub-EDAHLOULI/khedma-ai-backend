from fastapi import FastAPI

from app.exception_handlers import register_exception_handlers
from app.routers import jobs, profile

app = FastAPI()

register_exception_handlers(app)

app.include_router(jobs.router)
app.include_router(profile.router)


@app.get("/health")
def health():
    return {"status": "ok"}
