from fastapi import FastAPI

from app.routers import jobs, profile

app = FastAPI()

app.include_router(jobs.router)
app.include_router(profile.router)


@app.get("/health")
def health():
    return {"status": "ok"}
