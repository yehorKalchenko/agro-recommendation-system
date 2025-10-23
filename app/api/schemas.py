from typing import List, Optional
from pydantic import BaseModel, Field, conlist

SUPPORTED_CROPS = {"potato", "onion", "garlic", "tomato", "cucumber"}

class GeoPoint(BaseModel):
    lat: float
    lon: float

class DiagnoseRequest(BaseModel):
    crop: str = Field(description="one of supported crops")
    growth_stage: Optional[str] = None
    location: Optional[GeoPoint] = None
    symptoms_text: str = Field(min_length=5)

    def validate_crop(self):
        if self.crop not in SUPPORTED_CROPS:
            raise ValueError(f"Unsupported crop: {self.crop}")

class KBRef(BaseModel):
    id: str
    title: str

class Candidate(BaseModel):
    disease: str
    score: float = Field(ge=0, le=1)
    rationale: str
    kb_refs: Optional[conlist(KBRef, max_items=5)] = None

class ActionPlan(BaseModel):
    diagnostics: List[str] = []
    agronomy: List[str] = []
    chemical: List[str] = []  # textual placeholders in MVP
    bio: List[str] = []

class DiagnoseResponse(BaseModel):
    case_id: str
    candidates: List[Candidate]
    plan: ActionPlan
    disclaimers: List[str] = []
