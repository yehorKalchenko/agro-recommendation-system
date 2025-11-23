import json
from typing import List, Dict

from app.api.schemas import DiagnoseRequest
from app.core.config import settings
from app.services.llm import bedrock_client


def _rank_stub(req: DiagnoseRequest, candidates: List[Dict]) -> List[Dict]:
    alpha = settings.SCORING_ALPHA
    text = (req.symptoms_text or "").lower()

    result = []
    for c in candidates:
        s_rules = float(c.get("_rule_score", 0.0))
        s_ret = float(c.get("_score", 0.0))
        score = alpha * s_rules + (1.0 - alpha) * s_ret

        rationale_bits = []
        matched = [s for s in c.get("symptoms", []) if any(w in text for w in s.lower().split())]
        if matched:
            rationale_bits.append(f"Збіг симптомів: {', '.join(matched[:3])}")
        vp = c.get("visual_patterns", [])
        if any(k in " ".join(vp).lower() for k in ["powder", "мучнист", "downy", "пероноспор"]):
            rationale_bits.append("Візуальні ознаки відповідають опису в KB")
        if req.growth_stage and c.get("stage_window"):
            rationale_bits.append("Стадія росту врахована")

        result.append(
            {
                "name": c["name"],
                "score": round(min(max(score, 0.0), 1.0), 3),
                "rationale": "; ".join(rationale_bits) or "Гіпотеза на основі близькості симптомів у KB",
                "kb_refs": [{"id": c["id"], "name": c["name"]}],
                "actions": c.get("actions", {}),
            }
        )

    return sorted(result, key=lambda x: x["score"], reverse=True)


def _enrich_with_bedrock(req: DiagnoseRequest, ranked: List[Dict]) -> List[Dict]:

    if not ranked:
        return ranked

    if settings.BEDROCK_MODEL_ID and settings.BEDROCK_REGION:
        try:
            payload = {
                "symptoms_text": req.symptoms_text,
                "crop": req.crop,
                "growth_stage": req.growth_stage,
                "candidates": [
                    {
                        "name": c["name"],
                        "score": c["score"],
                        "rationale": c["rationale"],
                        "actions": c.get("actions", {}),
                    }
                    for c in ranked
                ],
            }
            llm_out = bedrock_client.generate_explanations(payload)
            for c, upd in zip(ranked, llm_out.get("candidates", [])):
                if "rationale" in upd:
                    c["rationale"] = upd["rationale"]
                if "actions" in upd:
                    c["actions"] = upd["actions"]
        except Exception:
            pass

    return ranked


def rank_and_reason(req: DiagnoseRequest, candidates: List[Dict]) -> List[Dict]:
    ranked = _rank_stub(req, candidates)

    if settings.LLM_MODE == "bedrock":
        ranked = _enrich_with_bedrock(req, ranked)

    return ranked
