from fastapi import FastAPI
from app.api.routes.diagnose import router as diagnose_router

app = FastAPI(title="AgroDiag MVP", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(diagnose_router, prefix="/v1")
