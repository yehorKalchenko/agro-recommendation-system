"""
Pipeline Orchestrator - Main coordinator for the diagnosis pipeline.

Coordinates the 6-stage diagnosis process:
1. Image preprocessing
2. Computer Vision (CVService)
3. Knowledge Base Retrieval (RAGRetriever)
4. Rules Engine (RulesHelper)
5. LLM Ranking (LLMClient)
6. Persistence (filesystem/database/S3)
"""
import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from io import BytesIO

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image, ExifTags

import logging

from app.api.schemas import (
    DiagnoseRequest,
    DiagnoseResponse,
    Candidate,
    ActionPlan,
    KBRef,
    DebugInfo
)
from app.core.config import settings
from app.services.cv_service import CVService
from app.services.rag_retriever import RAGRetriever
from app.services.llm_client import LLMClient
from app.services.helpers.rules_helper import RulesHelper

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Pipeline Orchestrator - Main coordinator for the diagnosis pipeline.

    This class orchestrates the entire diagnosis workflow using
    Dependency Injection pattern for service composition.

    Usage:
        orchestrator = PipelineOrchestrator()
        result = await orchestrator.run_pipeline(req, images, case_id, db)
    """

    def __init__(
        self,
        cv_service: Optional[CVService] = None,
        rag_retriever: Optional[RAGRetriever] = None,
        llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize Pipeline Orchestrator with optional service injection.

        Args:
            cv_service: Computer Vision Service (created if None)
            rag_retriever: RAG Retriever Service (created if None)
            llm_client: LLM Client Service (created if None)
        """
        self.cv_service = cv_service or CVService()
        self.rag_retriever = rag_retriever or RAGRetriever()
        self.llm_client = llm_client or LLMClient()
        self.rules_helper = RulesHelper()

        logger.info("PipelineOrchestrator initialized")


    async def run_pipeline(
        self,
        req: DiagnoseRequest,
        images: List[UploadFile],
        case_id: str,
        db: Optional[AsyncSession] = None,
        use_rekognition: Optional[bool] = None,
        use_bedrock: Optional[bool] = None
    ) -> DiagnoseResponse:
        """
        Execute the complete diagnosis pipeline.

        Pipeline stages:
        1. Image preprocessing and validation
        2. Computer Vision feature extraction
        3. Knowledge Base retrieval
        4. Rules Engine filtering
        5. LLM ranking and reasoning
        6. Response assembly
        7. Persistence (filesystem/database/S3)

        Args:
            req: Diagnosis request with symptoms and metadata
            images: List of uploaded images
            case_id: Unique case identifier (UUID)
            db: Optional database session for persistence
            use_rekognition: Override .env setting for Rekognition (True/False/None)
            use_bedrock: Override .env setting for Bedrock LLM (True/False/None)

        Returns:
            DiagnoseResponse with diagnosis results

        Raises:
            HTTPException: If validation fails or pipeline encounters critical error
        """
        t0 = time.perf_counter()
        case_uuid = uuid.UUID(case_id)

        logger.info(f"Starting pipeline for case {case_id}, crop={req.crop}")

        # ═══════════════════════════════════════════════════════
        # STAGE 0: Image Preprocessing
        # ═══════════════════════════════════════════════════════

        img_meta, images_bytes, exif_list = await self._preprocess_images(images)

        # ═══════════════════════════════════════════════════════
        # STAGE 1: Computer Vision
        # ═══════════════════════════════════════════════════════

        t_cv0 = time.perf_counter()
        visual_features = await self.cv_service.extract_features(
            images,
            req.symptoms_text,
            images_bytes=images_bytes,
            use_rekognition=use_rekognition
        )
        t_cv1 = time.perf_counter()

        logger.info(f"CV extracted {len(visual_features)} features in {t_cv1 - t_cv0:.2f}s")

        # ═══════════════════════════════════════════════════════
        # STAGE 2: Knowledge Base Retrieval
        # ═══════════════════════════════════════════════════════

        t_ret0 = time.perf_counter()
        kb_cards = await self.rag_retriever.retrieve(
            req.crop,
            req.symptoms_text,
            visual_features
        )
        t_ret1 = time.perf_counter()

        logger.info(f"RAG retrieved {len(kb_cards)} candidates in {t_ret1 - t_ret0:.2f}s")

        # ═══════════════════════════════════════════════════════
        # STAGE 3: Rules Engine
        # ═══════════════════════════════════════════════════════

        t_rules0 = time.perf_counter()
        rule_adjusted = self.rules_helper.apply_rules(
            req.crop,
            req.growth_stage,
            visual_features,
            kb_cards
        )
        t_rules1 = time.perf_counter()

        logger.info(f"Rules filtered to {len(rule_adjusted)} candidates in {t_rules1 - t_rules0:.2f}s")

        # ═══════════════════════════════════════════════════════
        # STAGE 4: LLM Ranking & Reasoning
        # ═══════════════════════════════════════════════════════

        t_rank0 = time.perf_counter()
        ranked = await self.llm_client.rank_and_reason(req, rule_adjusted, use_bedrock=use_bedrock)
        t_rank1 = time.perf_counter()

        logger.info(f"LLM ranked {len(ranked)} candidates in {t_rank1 - t_rank0:.2f}s")

        # ═══════════════════════════════════════════════════════
        # STAGE 5: Response Assembly
        # ═══════════════════════════════════════════════════════

        response = self._assemble_response(
            case_id,
            ranked,
            visual_features,
            t0,
            t_cv1 - t_cv0,
            t_ret1 - t_ret0,
            t_rules1 - t_rules0,
            t_rank1 - t_rank0
        )

        # ═══════════════════════════════════════════════════════
        # STAGE 6: Persistence
        # ═══════════════════════════════════════════════════════

        await self._persist_case(
            case_id,
            case_uuid,
            req,
            response,
            img_meta,
            images_bytes,
            exif_list,
            visual_features,
            db
        )

        total_time = time.perf_counter() - t0
        logger.info(f"Pipeline completed for case {case_id} in {total_time:.2f}s")

        return response


    async def _preprocess_images(
        self,
        images: List[UploadFile]
    ) -> tuple[List[Dict], List[bytes], List[Dict]]:
        """
        Preprocess and validate uploaded images.

        Args:
            images: List of uploaded images

        Returns:
            Tuple of (metadata, bytes, exif_data)

        Raises:
            HTTPException: If validation fails
        """
        # Validate image count
        if images and len(images) > settings.MAX_IMAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. MAX_IMAGES={settings.MAX_IMAGES}"
            )

        img_meta, images_bytes, exif_list = [], [], []
        allowed_mime = set(settings.ALLOWED_MIME)
        max_image_bytes = settings.MAX_IMAGE_MB * 1024 * 1024

        for i, f in enumerate(images or []):
            ctype = (getattr(f, "content_type", "") or "").lower()
            if ctype not in allowed_mime:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {ctype}"
                )

            fname = self._safe_filename(getattr(f, "filename", f"image_{i}.bin"))
            b = await f.read()

            if len(b) > max_image_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {fname} exceeds {settings.MAX_IMAGE_MB}MB"
                )

            # Extract EXIF data
            try:
                im = Image.open(BytesIO(b))
                exif = self._extract_exif(im)
                exif_list.append(exif)
            except Exception:
                exif = {"error": "not an image?"}
                exif_list.append(exif)

            images_bytes.append(b)
            img_meta.append({
                "filename": fname,
                "content_type": ctype,
                "bytes": len(b)
            })

        return img_meta, images_bytes, exif_list


    def _assemble_response(
        self,
        case_id: str,
        ranked: List[Dict],
        visual_features: Dict,
        t0: float,
        cv_time: float,
        ret_time: float,
        rules_time: float,
        rank_time: float
    ) -> DiagnoseResponse:
        """
        Assemble final DiagnoseResponse from pipeline results.

        Args:
            case_id: Case UUID
            ranked: Ranked disease candidates from LLMClient
            visual_features: Visual features from CVService
            t0: Pipeline start time
            cv_time: CV stage duration
            ret_time: Retrieval stage duration
            rules_time: Rules stage duration
            rank_time: Ranking stage duration

        Returns:
            Complete DiagnoseResponse
        """
        # Build candidates (top 3)
        candidates = [
            Candidate(
                disease=it["name"],
                score=it["score"],
                rationale=it["rationale"],
                kb_refs=[
                    KBRef(id=ref["id"], title=ref.get("name", ref["id"]))
                    for ref in it.get("kb_refs", [])
                ],
            )
            for it in ranked[:3]
        ]

        # Build action plan from top candidate
        plan = ActionPlan()
        if ranked:
            top_actions = ranked[0].get("actions", {})
            plan = ActionPlan(
                diagnostics=top_actions.get("diagnostics", []),
                agronomy=top_actions.get("agronomy", []),
                chemical=top_actions.get("chemical", []),
                bio=top_actions.get("bio", []),
            )

        # Disclaimers
        disclaimers = [
            "*MVP*: рекомендації носять ознайомчий характер. Перевіряйте місцеві регуляції щодо ЗЗР та використовуйте ЗІЗ.",
        ]

        # Timing info
        timings = {
            "cv": round(cv_time, 4),
            "retriever": round(ret_time, 4),
            "rules": round(rules_time, 4),
            "rank": round(rank_time, 4),
            "total": round(time.perf_counter() - t0, 4),
        }

        # Component info
        components = {
            "llm": settings.LLM_MODE,
            "retrieval": "keyword",
            "rules": "v0",
            "cv": "pillow" + ("+rekognition" if settings.USE_REKOGNITION else ""),
        }

        workspace_path = None
        if not settings.USE_DATABASE:
            workspace_path = f"./data/cases/{datetime.now().date().isoformat()}/{case_id}"

        debug = DebugInfo(
            timings=timings,
            components=components,
            workspace_path=workspace_path,
        )

        return DiagnoseResponse(
            case_id=case_id,
            candidates=candidates,
            plan=plan,
            disclaimers=disclaimers,
            visual_features=visual_features,
            debug=debug
        )


    async def _persist_case(
        self,
        case_id: str,
        case_uuid: uuid.UUID,
        req: DiagnoseRequest,
        resp: DiagnoseResponse,
        img_meta: List[Dict],
        images_bytes: List[bytes],
        exif_list: List[Dict],
        visual_features: Dict,
        db: Optional[AsyncSession]
    ):
        """
        Persist case data to filesystem or database.

        Args:
            case_id: Case UUID string
            case_uuid: Case UUID object
            req: Original request
            resp: Diagnosis response
            img_meta: Image metadata
            images_bytes: Image bytes
            exif_list: EXIF data
            visual_features: Visual features
            db: Optional database session
        """
        # Save to database if enabled
        if settings.USE_DATABASE and db is not None:
            try:
                await self._save_to_database(
                    db, case_uuid, req, resp, img_meta, images_bytes, exif_list, visual_features
                )
                return
            except Exception as e:
                logger.error(f"Database save failed: {e}", exc_info=True)
                logger.warning("Falling back to filesystem storage")

        # Fall back to filesystem (default)
        await self._save_to_filesystem(
            case_id, req, resp, img_meta, images_bytes, exif_list, visual_features
        )


    async def _save_to_filesystem(
        self,
        case_id: str,
        req: DiagnoseRequest,
        resp: DiagnoseResponse,
        img_meta: List[Dict],
        images_bytes: List[bytes],
        exif_list: List[Dict],
        visual_features: Dict
    ):
        """Save case data to filesystem (legacy mode)."""
        data_root = settings.DATA_ROOT
        date_str = datetime.now().date().isoformat()
        workspace = os.path.join(data_root, "cases", date_str, case_id)
        os.makedirs(os.path.join(workspace, "images"), exist_ok=True)

        # Save images
        for meta, img_bytes in zip(img_meta, images_bytes):
            fname = meta["filename"]
            with open(os.path.join(workspace, "images", fname), "wb") as out:
                out.write(img_bytes)

        # Save request
        req_dump = req.model_dump()
        req_dump["_images"] = img_meta
        with open(os.path.join(workspace, "request.json"), "w", encoding="utf-8") as fw:
            json.dump(req_dump, fw, ensure_ascii=False, indent=2)

        # Save trace
        with open(os.path.join(workspace, "trace.json"), "w", encoding="utf-8") as fw:
            json.dump(
                {
                    "visual_features": visual_features,
                    "cv_image_meta": img_meta,
                    "cv_exif": exif_list,
                    "timings": resp.debug.timings if resp.debug else {},
                },
                fw, ensure_ascii=False, indent=2
            )

        # Save response
        with open(os.path.join(workspace, "response.json"), "w", encoding="utf-8") as fw:
            json.dump(resp.model_dump(), fw, ensure_ascii=False, indent=2)

        logger.info(f"Saved case {case_id} to filesystem: {workspace}")


    async def _save_to_database(
        self,
        db: AsyncSession,
        case_uuid: uuid.UUID,
        req: DiagnoseRequest,
        resp: DiagnoseResponse,
        img_meta: List[Dict],
        images_bytes: List[bytes],
        exif_list: List[Dict],
        visual_features: Dict
    ):
        """Save case data to database."""
        try:
            from app.db.repository import DiagnosisCaseRepository, DiagnosisImageRepository

            # Save diagnosis case
            await DiagnosisCaseRepository.create(
                db=db,
                case_id=case_uuid,
                crop=req.crop,
                symptoms_text=req.symptoms_text,
                growth_stage=req.growth_stage,
                location_lat=req.location.lat if req.location else None,
                location_lon=req.location.lon if req.location else None,
                candidates=[c.model_dump() for c in resp.candidates],
                action_plan=resp.plan.model_dump(),
                disclaimers=resp.disclaimers,
                debug_info=resp.debug.model_dump() if resp.debug else None,
                visual_features=visual_features,
            )

            # Save images
            for meta, img_bytes, exif in zip(img_meta, images_bytes, exif_list):
                # Upload to S3 if enabled
                s3_url, s3_key = None, None
                if settings.USE_S3:
                    try:
                        from app.services.helpers.storage_helper import StorageHelper
                        storage = StorageHelper()
                        s3_url, s3_key = await storage.upload_image_async(
                            str(case_uuid), meta["filename"], img_bytes, meta["content_type"]
                        )
                    except Exception as e:
                        logger.warning(f"S3 upload failed: {e}, storing in DB")

                await DiagnosisImageRepository.create(
                    db=db,
                    case_id=case_uuid,
                    filename=meta["filename"],
                    content_type=meta["content_type"],
                    size_bytes=meta["bytes"],
                    image_data=img_bytes if not s3_url else None,
                    s3_url=s3_url,
                    s3_key=s3_key,
                    width=exif.get("width"),
                    height=exif.get("height"),
                    exif_data=exif,
                )

            logger.info(f"Saved case {case_uuid} to database")

        except ImportError:
            logger.warning("Database repository not available")
            raise


    @staticmethod
    def _safe_filename(name: str) -> str:
        """Sanitize filename to prevent path traversal."""
        bad = '<>:"/\\|?*'
        for ch in bad:
            name = name.replace(ch, "_")
        return name.strip() or "file"


    @staticmethod
    def _extract_exif(img: Image.Image) -> Dict:
        """Extract EXIF metadata from image."""
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
