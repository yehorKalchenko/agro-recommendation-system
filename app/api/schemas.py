from typing import List, Optional, Dict
from pydantic import BaseModel, Field

SUPPORTED_CROPS = {
    "potato", "onion", "garlic", "tomato", "cucumber",
    "pepper", "cabbage", "carrot", "beet", "wheat"
}

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
    kb_refs: Optional[List[KBRef]] = Field(default=None, max_length=5)

class ActionPlan(BaseModel):
    diagnostics: List[str] = []
    agronomy: List[str] = []
    chemical: List[str] = []  # textual placeholders in MVP
    bio: List[str] = []

class DebugInfo(BaseModel):
    timings: Dict[str, float] = Field(default_factory=dict) 
    components: Dict[str, str] = Field(default_factory=dict)
    workspace_path: Optional[str] = None

class DiagnoseResponse(BaseModel):
    case_id: str
    candidates: List[Candidate]
    plan: ActionPlan
    disclaimers: List[str] = []
    visual_features: Optional[Dict[str, float]] = None
    debug: Optional[DebugInfo] = None

class CaseSummary(BaseModel):
    case_id: str
    date: str
    crop: str
    symptoms_preview: str = Field(max_length=100)

class CaseListResponse(BaseModel):
    cases: List[CaseSummary]
    total: int
