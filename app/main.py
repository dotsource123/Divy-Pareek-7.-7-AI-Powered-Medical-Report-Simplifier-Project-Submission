from fastapi import FastAPI
from app.api.v1 import report_router

app = FastAPI(
    title="AI-Powered Medical Report Simplifier",
    description="A service to extract, normalize, and explain medical reports.",
    version="1.0.0"
)

app.include_router(
    report_router.router,
    prefix="/api/v1",
    tags=["Medical Reports"]
)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Medical Report Simplifier API!"}