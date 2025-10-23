import os, glob, yaml, math
from typing import Dict, List

KB_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "kb")

def _load_kb_cards(crop: str) -> List[Dict]:
    pattern = os.path.join(KB_ROOT, crop, "*.yaml")
    cards = []
    for path in glob.glob(pattern):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            data["id"] = f"kb:{crop}:{os.path.basename(path).replace('.yaml','')}"
            cards.append(data)
    return cards

KEYWORDS = ["плями", "наліт", "жовт", "в'ян", "водянист", "смуги", "пустули", "білий", "чорн", "мозаїк"]

def _score_card(text: str, feats: Dict[str, float], card: Dict) -> float:
    t = text.lower()
    base = sum(1 for k in KEYWORDS if k in t and any(k in s.lower() for s in card.get("symptoms", [])))
    if feats.get("white_powder") and any("powder" in v.lower() or "мучнист" in v.lower() for v in card.get("visual_patterns", [])):
        base += 2
    if feats.get("downy_mildew") and any("downy" in v.lower() or "пероноспор" in v.lower() for v in card.get("visual_patterns", [])):
        base += 2
    return 1 - math.exp(-base)

def retrieve_kb(crop: str, symptoms_text: str, feats: Dict) -> List[Dict]:
    cards = _load_kb_cards(crop)
    for c in cards:
        c["_score"] = _score_card(symptoms_text, feats, c)
    return sorted(cards, key=lambda x: x["_score"], reverse=True)
