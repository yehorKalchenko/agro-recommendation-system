"""
AWS S3 service for storing diagnosis images.
Provides both sync and async interfaces.
"""
from typing import Optional, List, Tuple
import logging
import uuid
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)

try:
    import aioboto3
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logger.info("AWS SDK not available - S3 storage unavailable")

from app.core.config import settings


class S3Unavailable(Exception):
    """Raised when S3 service is unavailable or misconfigured."""
    pass


def _get_s3_client():
    """Create synchronous S3 client."""
    if not AWS_AVAILABLE:
        raise S3Unavailable("AWS SDK not installed")

    if not settings.USE_S3:
        raise S3Unavailable("S3 storage is disabled")

    if not settings.S3_BUCKET:
        raise S3Unavailable("S3_BUCKET not configured")

    try:
        return boto3.client('s3', region_name=settings.S3_REGION)
    except (BotoCoreError, NoCredentialsError) as e:
        raise S3Unavailable(f"Failed to create S3 client: {e}")


async def _get_s3_client_async():
    """Create async S3 client."""
    if not AWS_AVAILABLE:
        raise S3Unavailable("AWS SDK not installed")

    if not settings.USE_S3:
        raise S3Unavailable("S3 storage is disabled")

    if not settings.S3_BUCKET:
        raise S3Unavailable("S3_BUCKET not configured")

    session = aioboto3.Session()
    return session.client('s3', region_name=settings.S3_REGION)


def _generate_s3_key(case_id: str, filename: str) -> str:
    """
    Generate S3 object key for an image.

    """
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    # Sanitize filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    return f"cases/{date_str}/{case_id}/{safe_filename}"


def upload_image_sync(
    case_id: str,
    filename: str,
    image_bytes: bytes,
    content_type: Optional[str] = None
) -> Tuple[str, str]:
    """
    Synchronously upload image to S3.

    Args:
        case_id: UUID of the diagnosis case
        filename: Original filename
        image_bytes: Image data
        content_type: MIME type (auto-detected if not provided)

    Returns:
        Tuple of (s3_url, s3_key)

    Raises:
        S3Unavailable: If S3 is not configured
        ClientError: If upload fails
    """
    client = _get_s3_client()
    s3_key = _generate_s3_key(case_id, filename)

    # Auto-detect content type if not provided
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

    try:
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type,
            Metadata={
                'case-id': case_id,
                'original-filename': filename
            }
        )

        # Generate S3 URL
        s3_url = f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{s3_key}"

        logger.info(f"Uploaded image to S3: {s3_key}")
        return s3_url, s3_key

    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        raise


async def upload_image_async(
    case_id: str,
    filename: str,
    image_bytes: bytes,
    content_type: Optional[str] = None
) -> Tuple[str, str]:
    """
    Asynchronously upload image to S3.

    Args:
        case_id: UUID of the diagnosis case
        filename: Original filename
        image_bytes: Image data
        content_type: MIME type (auto-detected if not provided)

    Returns:
        Tuple of (s3_url, s3_key)
    """
    async with await _get_s3_client_async() as client:
        s3_key = _generate_s3_key(case_id, filename)

        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"

        try:
            await client.put_object(
                Bucket=settings.S3_BUCKET,
                Key=s3_key,
                Body=image_bytes,
                ContentType=content_type,
                Metadata={
                    'case-id': case_id,
                    'original-filename': filename
                }
            )

            s3_url = f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{s3_key}"

            logger.info(f"Uploaded image to S3 (async): {s3_key}")
            return s3_url, s3_key

        except ClientError as e:
            logger.error(f"S3 async upload failed: {e}")
            raise


async def upload_images_batch_async(
    case_id: str,
    images: List[Tuple[str, bytes, str]]
) -> List[Tuple[str, str]]:
    """
    Upload multiple images concurrently.

    Args:
        case_id: UUID of the diagnosis case
        images: List of (filename, image_bytes, content_type) tuples

    Returns:
        List of (s3_url, s3_key) tuples
    """
    import asyncio

    tasks = [
        upload_image_async(case_id, filename, image_bytes, content_type)
        for filename, image_bytes, content_type in images
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    successful = [r for r in results if not isinstance(r, Exception)]

    logger.info(f"Batch uploaded {len(successful)}/{len(images)} images")
    return successful


def get_signed_url_sync(s3_key: str, expires_in: int = 3600) -> str:
    """
    Generate presigned URL for downloading an image.

    Args:
        s3_key: S3 object key
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Presigned URL
    """
    client = _get_s3_client()

    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.S3_BUCKET,
                'Key': s3_key
            },
            ExpiresIn=expires_in
        )
        return url

    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise


async def get_signed_url_async(s3_key: str, expires_in: int = 3600) -> str:
    """
    Async version of presigned URL generation.
    """
    async with await _get_s3_client_async() as client:
        try:
            url = await client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.S3_BUCKET,
                    'Key': s3_key
                },
                ExpiresIn=expires_in
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL (async): {e}")
            raise


def delete_image_sync(s3_key: str) -> bool:
    """
    Delete an image from S3.

    Args:
        s3_key: S3 object key

    Returns:
        True if successful
    """
    client = _get_s3_client()

    try:
        client.delete_object(
            Bucket=settings.S3_BUCKET,
            Key=s3_key
        )
        logger.info(f"Deleted image from S3: {s3_key}")
        return True

    except ClientError as e:
        logger.error(f"S3 delete failed: {e}")
        return False


async def delete_image_async(s3_key: str) -> bool:
    """
    Async version of image deletion.
    """
    async with await _get_s3_client_async() as client:
        try:
            await client.delete_object(
                Bucket=settings.S3_BUCKET,
                Key=s3_key
            )
            logger.info(f"Deleted image from S3 (async): {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"S3 async delete failed: {e}")
            return False
