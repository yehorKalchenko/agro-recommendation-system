import os, json, datetime, time
from typing import List
from fastapi import UploadFile, HTTPException
from app.api.schemas import DiagnoseRequest, DiagnoseResponse, Candidate, ActionPlan, KBRef, DebugInfo
from app.services.cv.stub import extract_visual_features
from app.services.rules.engine import apply_rules
from app.services.rag.retriever import retrieve_kb
from app.services.llm.client import rank_and_reason
from io import BytesIO
from PIL import Image, ExifTags

ALLOWED_MIME = set((os.getenv("ALLOWED_MIME") or "image/jpeg,image/png,image/webp").split(","))
MAX_IMAGES = int(os.getenv("MAX_IMAGES", "4"))
MAX_IMAGE_MB = int(os.getenv("MAX_IMAGE_MB", "5"))
MAX_IMAGE_BYTES = MAX_IMAGE_MB * 1024 * 1024

def _now_date_str():
    return datetime.date.today().isoformat()

def _safe_name(name: str) -> str:
    bad = '<>:"/\\|?*'
    for ch in bad:
        name = name.replace(ch, "_")
    return name.strip() or "file"

def _exif_summary(img: Image.Image):
    summary = {"width": img.width, "height": img.height}
    try:
        raw = img._getexif() or {}
        tag_by_id = {ExifTags.TAGS.get(k, str(k)): v for k, v in raw.items()}
        for k in ("DateTimeOriginal", "Model", "Orientation"):
            if k in tag_by_id:
                summary[k] = tag_by_id[k]
    except Exception:
        pass
    return summary

async def run_pipeline(req: DiagnoseRequest, images: List[UploadFile], case_id: str) -> DiagnoseResponse:
    t0 = time.perf_counter()

    if images and len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Забагато файлів. MAX_IMAGES={MAX_IMAGES}")

    data_root = os.getenv("DATA_ROOT", "./data")
    workspace = os.path.join(data_root, "cases", _now_date_str(), case_id)
    os.makedirs(os.path.join(workspace, "images"), exist_ok=True)

    img_meta, images_bytes, exif_list = [], [], []
    for i, f in enumerate(images or []):
        ctype = (getattr(f, "content_type", "") or "").lower()
        if ctype not in ALLOWED_MIME:
            raise HTTPException(status_code=400, detail=f"Непідтримуваний тип: {ctype}")

        fname = _safe_name(getattr(f, "filename", f"image_{i}.bin"))
        b = await f.read()
        if len(b) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail=f"Файл {fname} перевищує {MAX_IMAGE_MB}MB")

        try:
            im = Image.open(BytesIO(b))
            exif_list.append(_exif_summary(im))
        except Exception:
            exif_list.append({"error": "not an image?"})

        with open(os.path.join(workspace, "images", fname), "wb") as out:
            out.write(b)

        images_bytes.append(b)
        img_meta.append({"filename": fname, "content_type": ctype, "bytes": len(b)})

    req_dump = req.model_dump()
    req_dump["_images"] = img_meta
    with open(os.path.join(workspace, "request.json"), "w", encoding="utf-8") as fw:
        json.dump(req_dump, fw, ensure_ascii=False, indent=2)

    t_cv0 = time.perf_counter()
    visual_feats = await extract_visual_features(images, req.symptoms_text, images_bytes=images_bytes)
    t_cv1 = time.perf_counter()

    t_ret0 = time.perf_counter()
    kb_cards = retrieve_kb(req.crop, req.symptoms_text, visual_feats)
    t_ret1 = time.perf_counter()

    t_rules0 = time.perf_counter()
    rule_adjusted = apply_rules(req.crop, req.growth_stage, visual_feats, kb_cards)
    t_rules1 = time.perf_counter()

    t_rank0 = time.perf_counter()
    ranked = rank_and_reason(req, rule_adjusted)
    t_rank1 = time.perf_counter()

    candidates = [
    Candidate(
        disease=it["name"],
        score=it["score"],
        rationale=it["rationale"],
        kb_refs=[KBRef(id=card["id"], title=card.get("name", card["id"])) for card in it.get("kb_refs", [])],
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

    timings = {
        "cv": round(t_cv1 - t_cv0, 4),
        "retriever": round(t_ret1 - t_ret0, 4),
        "rules": round(t_rules1 - t_rules0, 4),
        "rank": round(t_rank1 - t_rank0, 4),
        "total": round(time.perf_counter() - t0, 4),
    }
    debug = DebugInfo(
        timings=timings,
        components={"llm": "stub", "retrieval": "keyword", "rules": "v0", "cv": "stub+pillow"},
        workspace_path=workspace,
    )

    resp = DiagnoseResponse(case_id=case_id, candidates=candidates, plan=plan, disclaimers=disclaimers, debug=debug)

    with open(os.path.join(workspace, "trace.json"), "w", encoding="utf-8") as fw:
        json.dump(
            {
                "visual_feats": visual_feats,
                "cv_image_meta": img_meta,
                "cv_exif": exif_list,
                "timings": timings,
            },
            fw, ensure_ascii=False, indent=2
        )
    with open(os.path.join(workspace, "response.json"), "w", encoding="utf-8") as fw:
        json.dump(resp.model_dump(), fw, ensure_ascii=False, indent=2)

    return resp