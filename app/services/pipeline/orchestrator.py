from typing import List
from fastapi import UploadFile
from app.api.schemas import DiagnoseRequest, DiagnoseResponse, Candidate, ActionPlan, KBRef
from app.services.cv.stub import extract_visual_features
from app.services.rules.engine import apply_rules
from app.services.rag.retriever import retrieve_kb
from app.services.llm.client import rank_and_reason

async def run_pipeline(req: DiagnoseRequest, images: List[UploadFile], case_id: str) -> DiagnoseResponse:
    visual_feats = await extract_visual_features(images, req.symptoms_text)
    kb_cards = retrieve_kb(req.crop, req.symptoms_text, visual_feats)
    rule_adjusted = apply_rules(req.crop, req.growth_stage, visual_feats, kb_cards)
    ranked = rank_and_reason(req, rule_adjusted)

    candidates = [
        Candidate(
            disease=it["name"],
            score=it["score"],
            rationale=it["rationale"],
            kb_refs=[KBRef(id=card["id"], title=card["name"]) for card in it.get("kb_refs", [])],
        )
        for it in ranked[:3]
    ]

    plan = ActionPlan(
        diagnostics=ranked[0].get("actions", {}).get("diagnostics", []) if ranked else [],
        agronomy=ranked[0].get("actions", {}).get("agronomy", []) if ranked else [],
        chemical=ranked[0].get("actions", {}).get("chemical", []) if ranked else [],
        bio=ranked[0].get("actions", {}).get("bio", []) if ranked else [],
    )

    disclaimers = [
        "*MVP*: рекомендації носять ознайомчий характер. Перевіряйте місцеві регуляції щодо ЗЗР та використовуйте ЗІЗ.",
    ]

    return DiagnoseResponse(case_id=case_id, candidates=candidates, plan=plan, disclaimers=disclaimers)
