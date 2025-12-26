import uuid
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Header
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DiagnoseRequest, DiagnoseResponse, CaseSummary, CaseListResponse
from app.services.orchestrator import PipelineOrchestrator
from app.core.config import settings

# Optional database import
try:
    from app.db.database import get_db as _get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    _get_db = None


async def get_db_if_enabled():
    """Dependency that returns DB session only if database is enabled."""
    if DB_AVAILABLE and settings.USE_DATABASE and _get_db is not None:
        async for session in _get_db():
            yield session
    else:
        yield None


router = APIRouter(tags=["diagnose"])


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    crop: str = Form(...),
    symptoms_text: str = Form(...),
    growth_stage: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    db: Optional[AsyncSession] = Depends(get_db_if_enabled),
    x_use_rekognition: Optional[str] = Header(None, alias="X-Use-Rekognition"),
    x_use_bedrock: Optional[str] = Header(None, alias="X-Use-Bedrock"),
):
    """
    Diagnose plant disease from symptoms and images.

    Supports:
    - Text-only diagnosis (symptoms_text required)
    - Image-based diagnosis (optional images)
    - Database storage (if USE_DATABASE=true)
    - AWS Rekognition (if USE_REKOGNITION=true)
    - AWS Bedrock LLM (if LLM_MODE=bedrock)
    """
    req = DiagnoseRequest(
        crop=crop,
        growth_stage=growth_stage,
        location=None if lat is None or lon is None else {"lat": lat, "lon": lon},
        symptoms_text=symptoms_text,
    )
    try:
        req.validate_crop()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    case_id = str(uuid.uuid4())

    use_rekognition = None
    use_bedrock = None

    if x_use_rekognition is not None:
        use_rekognition = x_use_rekognition.lower() == "true"

    if x_use_bedrock is not None:
        use_bedrock = x_use_bedrock.lower() == "true"

    # Initialize orchestrator and run pipeline
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.run_pipeline(
        req,
        images or [],
        case_id,
        db=db,
        use_rekognition=use_rekognition,
        use_bedrock=use_bedrock
    )
    return result


@router.get("/cases/{case_id}", response_model=DiagnoseResponse)
async def get_case(
    case_id: str,
    db: Optional[AsyncSession] = Depends(get_db_if_enabled)
):
    """
    Retrieve a previously saved diagnosis case by ID.

    Args:
        case_id: UUID of the diagnosis case
        db: Optional database session

    Returns:
        Complete diagnosis response from the saved case

    Raises:
        404: Case not found
        500: Case data corrupted or unreadable
    """
    # Validate case_id format (basic UUID check)
    if not case_id or len(case_id) < 10 or len(case_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid case_id format")

    # Sanitize case_id to prevent path traversal
    safe_case_id = "".join(c for c in case_id if c.isalnum() or c in "-_")
    if safe_case_id != case_id:
        raise HTTPException(status_code=400, detail="Invalid characters in case_id")

    # Try database first if enabled
    if settings.USE_DATABASE and db is not None:
        try:
            from app.db.repository import DiagnosisCaseRepository
            import uuid as uuid_module

            case_uuid = uuid_module.UUID(case_id)
            case_db = await DiagnosisCaseRepository.get_by_id(db, case_uuid)

            if case_db:
                # Reconstruct DiagnoseResponse from database
                from app.api.schemas import Candidate, ActionPlan, DebugInfo

                candidates = [Candidate(**c) for c in case_db.candidates] if case_db.candidates else []
                plan = ActionPlan(**case_db.action_plan) if case_db.action_plan else ActionPlan()
                debug = DebugInfo(**case_db.debug_info) if case_db.debug_info else None

                return DiagnoseResponse(
                    case_id=str(case_db.id),
                    candidates=candidates,
                    plan=plan,
                    disclaimers=case_db.disclaimers or [],
                    visual_features=case_db.visual_features or {},
                    debug=debug
                )

        except ValueError:
            pass  # Invalid UUID, fall back to filesystem
        except ImportError:
            pass  # Repository not available
        except Exception as e:
            import logging
            logging.error(f"Database retrieval failed: {e}", exc_info=True)
            pass  # Fall back to filesystem

    # Search for case in date-partitioned directory structure
    cases_root = Path(settings.DATA_ROOT) / "cases"

    if not cases_root.exists():
        raise HTTPException(status_code=404, detail="No cases found")

    # Search all date directories for the case_id
    response_path = None
    for date_dir in cases_root.iterdir():
        if date_dir.is_dir():
            candidate_path = date_dir / case_id / "response.json"
            if candidate_path.exists():
                response_path = candidate_path
                break

    if not response_path:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_id} not found"
        )

    # Load and validate response
    try:
        with open(response_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate it matches our schema
        response = DiagnoseResponse(**data)
        return response

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Case data is corrupted"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load case: {str(e)}"
        )


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    date: Optional[str] = None,
    limit: int = 50,
    db: Optional[AsyncSession] = Depends(get_db_if_enabled)
):
    """
    List all diagnosis cases, optionally filtered by date.

    Args:
        date: Optional ISO date filter (YYYY-MM-DD)
        limit: Maximum number of cases to return (default 50)
        db: Optional database session

    Returns:
        List of case summaries with metadata
    """
    # Try database first if enabled
    if settings.USE_DATABASE and db is not None:
        try:
            import logging as log
            log.info(f"Cases History: Querying database (USE_DATABASE={settings.USE_DATABASE}, db={'present' if db else 'None'})")

            from app.db.repository import DiagnosisCaseRepository
            from sqlalchemy import select, func
            from app.db.models import DiagnosisCase

            # Build query
            stmt = select(DiagnosisCase).order_by(DiagnosisCase.created_at.desc()).limit(limit)

            if date:
                # Filter by date
                from datetime import datetime as dt
                try:
                    target_date = dt.fromisoformat(date).date()
                    stmt = stmt.where(func.date(DiagnosisCase.created_at) == target_date)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

            log.info(f"Executing query for cases (limit={limit}, date={date})")
            result = await db.execute(stmt)
            cases_db = result.scalars().all()
            log.info(f"Query returned {len(cases_db)} cases from database")

            summaries = [
                CaseSummary(
                    case_id=str(case.id),
                    date=case.created_at.date().isoformat(),
                    crop=case.crop,
                    symptoms_preview=case.symptoms_text[:100] if case.symptoms_text else ""
                )
                for case in cases_db
            ]

            log.info(f"Returning {len(summaries)} case summaries from database")
            return CaseListResponse(cases=summaries, total=len(summaries))

        except ImportError as e:
            import logging as log
            log.error(f"ImportError in /cases: {e}", exc_info=True)
            pass  # Fall back to filesystem
        except Exception as e:
            import logging as log
            log.error(f"Database query failed in /cases: {e}", exc_info=True)
            pass  # Fall back to filesystem

    # Fallback to filesystem
    cases_root = Path(settings.DATA_ROOT) / "cases"

    if not cases_root.exists():
        return CaseListResponse(cases=[], total=0)

    summaries = []

    # Determine which date directories to scan
    date_dirs = []
    if date:
        # Validate date format
        try:
            datetime.fromisoformat(date)
            target_dir = cases_root / date
            if target_dir.exists():
                date_dirs = [target_dir]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        # Scan all date directories
        date_dirs = [d for d in cases_root.iterdir() if d.is_dir()]

    # Collect case summaries
    for date_dir in sorted(date_dirs, reverse=True):  # Most recent first
        if len(summaries) >= limit:
            break

        for case_dir in date_dir.iterdir():
            if not case_dir.is_dir():
                continue

            request_file = case_dir / "request.json"
            if not request_file.exists():
                continue

            try:
                with open(request_file, "r", encoding="utf-8") as f:
                    req_data = json.load(f)

                summaries.append(CaseSummary(
                    case_id=case_dir.name,
                    date=date_dir.name,
                    crop=req_data.get("crop", "unknown"),
                    symptoms_preview=req_data.get("symptoms_text", "")[:100]
                ))

                if len(summaries) >= limit:
                    break

            except (json.JSONDecodeError, KeyError):
                continue  # Skip corrupted cases

    return CaseListResponse(cases=summaries, total=len(summaries))
