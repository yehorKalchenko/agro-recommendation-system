import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from app.api.schemas import DiagnoseRequest, DiagnoseResponse
from app.services.pipeline.orchestrator import run_pipeline

router = APIRouter(tags=["diagnose"])

@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    crop: str = Form(...),
    symptoms_text: str = Form(...),
    growth_stage: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
):
    req = DiagnoseRequest(
        crop=crop,
        growth_stage=growth_stage,
        location=None if lat is None or lon is None else {"lat": lat, "lon": lon},
        symptoms_text=symptoms_text,
    )
    try:
        req.validate_crop()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    case_id = str(uuid.uuid4())
    result = await run_pipeline(req, images or [], case_id)
    return result
