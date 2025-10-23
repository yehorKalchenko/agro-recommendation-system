from typing import List, Dict

def apply_rules(crop: str, growth_stage: str, feats: Dict, kb_cards: List[Dict]) -> List[Dict]:
    out = []
    for c in kb_cards:
        if crop not in c.get("crops_supported", []):
            continue
        score = c.get("_score", 0)
        stages = c.get("stage_window", [])
        if growth_stage and stages and growth_stage not in stages:
            score *= 0.8
        if feats.get("white_powder") and "powdery" in " ".join(c.get("visual_patterns", [])).lower():
            score += 0.1
        c["_rule_score"] = min(score, 1.0)
        out.append(c)
    return sorted(out, key=lambda x: x["_rule_score"], reverse=True)
