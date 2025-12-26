"""
Repository layer for database operations.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DiagnosisCase, DiagnosisImage, APIKey, UsageMetric
import uuid


class DiagnosisCaseRepository:
    """Repository for diagnosis cases."""

    @staticmethod
    async def create(
        db: AsyncSession,
        case_id: uuid.UUID,
        crop: str,
        symptoms_text: str,
        candidates: list,
        action_plan: dict,
        growth_stage: Optional[str] = None,
        location_lat: Optional[float] = None,
        location_lon: Optional[float] = None,
        disclaimers: Optional[list] = None,
        debug_info: Optional[dict] = None,
        visual_features: Optional[dict] = None,
    ) -> DiagnosisCase:
        """Create a new diagnosis case."""
        case = DiagnosisCase(
            id=case_id,
            crop=crop,
            growth_stage=growth_stage,
            symptoms_text=symptoms_text,
            location_lat=location_lat,
            location_lon=location_lon,
            candidates=candidates,
            action_plan=action_plan,
            disclaimers=disclaimers or [],
            debug_info=debug_info,
            visual_features=visual_features,
        )
        db.add(case)
        await db.flush()
        return case

    @staticmethod
    async def get_by_id(db: AsyncSession, case_id: uuid.UUID) -> Optional[DiagnosisCase]:
        """Get case by ID."""
        result = await db.execute(
            select(DiagnosisCase).where(DiagnosisCase.id == case_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_cases(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        crop: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> List[DiagnosisCase]:
        """List cases with optional filters."""
        query = select(DiagnosisCase).order_by(DiagnosisCase.created_at.desc())

        if crop:
            query = query.where(DiagnosisCase.crop == crop)

        if date:
            # Filter by date (start and end of day)
            start = datetime(date.year, date.month, date.day)
            end = start + timedelta(days=1)
            query = query.where(
                and_(
                    DiagnosisCase.created_at >= start,
                    DiagnosisCase.created_at < end
                )
            )

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_cases(
        db: AsyncSession,
        crop: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> int:
        """Count total cases with optional filters."""
        query = select(func.count(DiagnosisCase.id))

        if crop:
            query = query.where(DiagnosisCase.crop == crop)

        if date:
            start = datetime(date.year, date.month, date.day)
            end = start + timedelta(days=1)
            query = query.where(
                and_(
                    DiagnosisCase.created_at >= start,
                    DiagnosisCase.created_at < end
                )
            )

        result = await db.execute(query)
        return result.scalar_one()


class DiagnosisImageRepository:
    """Repository for diagnosis images."""

    @staticmethod
    async def create(
        db: AsyncSession,
        case_id: uuid.UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
        image_data: Optional[bytes] = None,
        s3_url: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        exif_data: Optional[dict] = None,
    ) -> DiagnosisImage:
        """Create a new diagnosis image."""
        image = DiagnosisImage(
            case_id=case_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            image_data=image_data,
            s3_url=s3_url,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            width=width,
            height=height,
            exif_data=exif_data,
        )
        db.add(image)
        await db.flush()
        return image

    @staticmethod
    async def get_by_case_id(db: AsyncSession, case_id: uuid.UUID) -> List[DiagnosisImage]:
        """Get all images for a case."""
        result = await db.execute(
            select(DiagnosisImage)
            .where(DiagnosisImage.case_id == case_id)
            .order_by(DiagnosisImage.uploaded_at)
        )
        return list(result.scalars().all())


class APIKeyRepository:
    """Repository for API keys."""

    @staticmethod
    async def create(
        db: AsyncSession,
        key_hash: str,
        key_name: str,
        created_by: Optional[str] = None,
        rate_limit_per_minute: int = 60,
        notes: Optional[str] = None,
    ) -> APIKey:
        """Create a new API key."""
        api_key = APIKey(
            key_hash=key_hash,
            key_name=key_name,
            created_by=created_by,
            rate_limit_per_minute=rate_limit_per_minute,
            notes=notes,
        )
        db.add(api_key)
        await db.flush()
        return api_key

    @staticmethod
    async def get_by_hash(db: AsyncSession, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == 1
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_usage(db: AsyncSession, api_key: APIKey):
        """Update last used timestamp and increment request count."""
        api_key.last_used_at = datetime.utcnow()
        api_key.total_requests += 1
        await db.flush()


class UsageMetricRepository:
    """Repository for usage metrics."""

    @staticmethod
    async def create(
        db: AsyncSession,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        crop: Optional[str] = None,
        cv_time_ms: Optional[float] = None,
        retrieval_time_ms: Optional[float] = None,
        rules_time_ms: Optional[float] = None,
        llm_time_ms: Optional[float] = None,
        api_key_id: Optional[uuid.UUID] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> UsageMetric:
        """Create a new usage metric."""
        metric = UsageMetric(
            endpoint=endpoint,
            method=method,
            crop=crop,
            response_time_ms=response_time_ms,
            status_code=status_code,
            cv_time_ms=cv_time_ms,
            retrieval_time_ms=retrieval_time_ms,
            rules_time_ms=rules_time_ms,
            llm_time_ms=llm_time_ms,
            api_key_id=api_key_id,
            error_type=error_type,
            error_message=error_message,
        )
        db.add(metric)
        # Don't flush - metrics can be committed async
        return metric
