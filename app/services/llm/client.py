from typing import List, Dict
from app.api.schemas import DiagnoseRequest

def rank_and_reason(req: DiagnoseRequest, candidates: List[Dict]) -> List[Dict]:
    result = []
    text = (req.symptoms_text or "").lower()
    for c in candidates:
        score = 0.5 * c.get("_rule_score", 0) + 0.5 * c.get("_score", 0)
        rationale_bits = []
        matched = [s for s in c.get("symptoms", []) if any(w in text for w in s.lower().split())]
        if matched:
            rationale_bits.append(f"Збіг симптомів: {', '.join(matched[:3])}")
        vp = c.get("visual_patterns", [])
        if any(k in ' '.join(vp).lower() for k in ["powder", "мучнист", "downy", "пероноспор"]):
            rationale_bits.append("Візуальні ознаки відповідають опису в KB")
        if req.growth_stage and c.get("stage_window"):
            rationale_bits.append("Стадія росту врахована")
        rationale = "; ".join(rationale_bits) or "Гіпотеза на основі близькості симптомів у KB"
        result.append({
            "name": c["name"],
            "score": round(min(max(score, 0.0), 1.0), 3),
            "rationale": rationale,
            "kb_refs": [{"id": c["id"], "name": c["name"]}],
            "actions": c.get("actions", {}),
        })
    return sorted(result, key=lambda x: x["score"], reverse=True)
