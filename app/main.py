from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.response import ApiResponse
from app.routers import jobs, profile

app = FastAPI()

app.include_router(jobs.router)
app.include_router(profile.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=ApiResponse.fail("Validation failed", errors).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.fail(exc.detail).model_dump(),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
