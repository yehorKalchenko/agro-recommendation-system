"""
SQLAlchemy models for AgroDiag database.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, LargeBinary, Float, Integer, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

Base = declarative_base()


class DiagnosisCase(Base):
    """Stores diagnosis request and response."""
    __tablename__ = "diagnosis_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Request data
    crop = Column(String(50), nullable=False, index=True)
    growth_stage = Column(String(50), nullable=True)
    symptoms_text = Column(Text, nullable=False)
    location_lat = Column(Float, nullable=True)
    location_lon = Column(Float, nullable=True)

    # Response data (stored as JSONB for flexibility)
    candidates = Column(JSONB, nullable=False)  # List of disease candidates
    action_plan = Column(JSONB, nullable=False)  # Diagnostic/agronomy/chemical/bio actions
    disclaimers = Column(JSONB, nullable=True)

    # Debug/metadata
    debug_info = Column(JSONB, nullable=True)  # Timings, components used, etc.
    visual_features = Column(JSONB, nullable=True)  # Extracted CV features

    # Indexes for common queries
    __table_args__ = (
        Index('idx_created_crop', 'created_at', 'crop'),
        Index('idx_symptoms_text_gin', 'symptoms_text', postgresql_using='gin', postgresql_ops={'symptoms_text': 'gin_trgm_ops'}),
    )


class DiagnosisImage(Base):
    """Stores images associated with diagnosis cases."""
    __tablename__ = "diagnosis_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)

    # Storage options:
    # Option 1: Store image data directly in DB (small deployments)
    image_data = Column(LargeBinary, nullable=True)

    # Option 2: Store S3 URL (production)
    s3_url = Column(String(512), nullable=True)
    s3_bucket = Column(String(128), nullable=True)
    s3_key = Column(String(512), nullable=True)

    # Image metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    exif_data = Column(JSONB, nullable=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_case_images', 'case_id', 'uploaded_at'),
    )


class APIKey(Base):
    """API keys for authentication."""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    key_name = Column(String(100), nullable=False)  # Friendly name

    # Permissions
    is_active = Column(Integer, default=1, nullable=False)  # 1=active, 0=revoked
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)

    # Usage tracking
    total_requests = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)  # Email or username
    notes = Column(Text, nullable=True)


class UsageMetric(Base):
    """Tracks API usage for monitoring and analytics."""
    __tablename__ = "usage_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Request details
    endpoint = Column(String(100), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    crop = Column(String(50), nullable=True, index=True)

    # Performance
    response_time_ms = Column(Float, nullable=False)
    status_code = Column(Integer, nullable=False)

    # Components timing
    cv_time_ms = Column(Float, nullable=True)
    retrieval_time_ms = Column(Float, nullable=True)
    rules_time_ms = Column(Float, nullable=True)
    llm_time_ms = Column(Float, nullable=True)

    # API key tracking (nullable for public access)
    api_key_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Error tracking
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_timestamp_endpoint', 'timestamp', 'endpoint'),
    )
