from typing import List, Dict
from fastapi import UploadFile

async def extract_visual_features(images: List[UploadFile], symptoms_text: str) -> Dict[str, float]:
    text = (symptoms_text or "").lower()
    feats = {
        "lesion_spots": 1.0 if any(k in text for k in ["плями", "плям", "пятна", "spots", "lesions"]) else 0.0,
        "white_powder": 1.0 if any(k in text for k in ["білий наліт", "мучнист", "powdery"]) else 0.0,
        "downy_mildew": 1.0 if any(k in text for k in ["пероноспор", "несправж", "downy"]) else 0.0,
        "wilting": 1.0 if any(k in text for k in ["в'ян", "вян", "wilting"]) else 0.0,
        "yellowing": 1.0 if any(k in text for k in ["жовт", "yellow"]) else 0.0,
        "black_spots": 1.0 if any(k in text for k in ["чорн", "black spot"]) else 0.0,
        "water_soaked": 1.0 if any(k in text for k in ["водянист", "water-soaked"]) else 0.0,
    }
    return feats
