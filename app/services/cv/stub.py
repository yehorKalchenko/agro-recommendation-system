from typing import List, Dict, Optional
from fastapi import UploadFile
from io import BytesIO
from PIL import Image, ImageFilter

_DEF_SIZE = (64, 64)

def _image_stats_from_bytes(images_bytes: List[bytes]) -> Dict[str, float]:
    if not images_bytes:
        return {}

    white_like = 0.0
    very_dark = 0.0
    edges_mean = 0.0

    n = 0
    for b in images_bytes:
        try:
            im = Image.open(BytesIO(b)).convert("RGB")
            im = im.resize(_DEF_SIZE)
        except Exception:
            continue

        px = im.load()
        w, h = im.size
        total = w * h
        white_cnt, dark_cnt = 0, 0

        for y in range(h):
            for x in range(w):
                r, g, b = px[x, y]
                v = max(r, g, b) / 255.0
                near_gray = (abs(r - g) < 18 and abs(g - b) < 18 and abs(r - b) < 18)
                if near_gray and v > 0.75:
                    white_cnt += 1
                if v < 0.18:
                    dark_cnt += 1

        edges = im.filter(ImageFilter.FIND_EDGES).convert("L")
        edges_val = sum(edges.getdata()) / (255.0 * total)

        white_like += white_cnt / total
        very_dark  += dark_cnt / total
        edges_mean += edges_val
        n += 1

    if n == 0:
        return {}

    white_like /= n
    very_dark  /= n
    edges_mean /= n

    # Грубі бінарні сигнали
    return {
        "white_powder_img": 1.0 if white_like > 0.35 else 0.0,
        "water_soaked_img": 1.0 if very_dark  > 0.15 else 0.0,
        "lesion_spots_img": 1.0 if edges_mean > 0.25 else 0.0,
        "_white_like": round(white_like, 3),
        "_very_dark": round(very_dark, 3),
        "_edges_mean": round(edges_mean, 3),
    }

async def extract_visual_features(
    images: List[UploadFile],
    symptoms_text: str,
    images_bytes: Optional[List[bytes]] = None,
) -> Dict[str, float]:
    text = (symptoms_text or "").lower()
    feats = {
        "lesion_spots": 1.0 if any(k in text for k in ["плями", "плям", "пятна", "spots", "lesions"]) else 0.0,
        "white_powder": 1.0 if any(k in text for k in ["білий наліт", "мучнист", "powdery"]) else 0.0,
        "downy_mildew": 1.0 if any(k in text for k in ["пероноспор", "несправж", "downy"]) else 0.0,
        "wilting":      1.0 if any(k in text for k in ["в'ян", "вян", "wilting"]) else 0.0,
        "yellowing":    1.0 if any(k in text for k in ["жовт", "yellow"]) else 0.0,
        "black_spots":  1.0 if any(k in text for k in ["чорн", "black spot"]) else 0.0,
        "water_soaked": 1.0 if any(k in text for k in ["водянист", "water-soaked"]) else 0.0,
    }

    if images_bytes:
        img_signals = _image_stats_from_bytes(images_bytes)
        feats.update(img_signals)

    return feats
