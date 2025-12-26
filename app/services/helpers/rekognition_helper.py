"""
AWS Rekognition Helper for disease detection.
Extracted from cv/rekognition_adapter.py for cleaner architecture.
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.info("boto3 not installed - Rekognition unavailable")

from app.core.config import settings


class RekognitionUnavailable(Exception):
    """Raised when Rekognition service is not available or configured."""
    pass


# Mapping from Rekognition Custom Labels to Knowledge Base disease names
REKOGNITION_TO_KB_MAPPING = {
    "pepper_bacterial_spot": "bacterial_spot",
    "potato_early_blight": "early_blight",
    "potato_late_blight": "late_blight",
    "tomato_mold": "powdery_mildew",
    "tomato_blight": "late_blight",
    "tomato_spot": "bacterial_speck",
}


class RekognitionHelper:
    """Helper class for AWS Rekognition operations."""

    def __init__(self):
        """Initialize Rekognition client."""
        if not BOTO3_AVAILABLE:
            raise RekognitionUnavailable("boto3 not installed")

        if not settings.REKOGNITION_REGION:
            raise RekognitionUnavailable("REKOGNITION_REGION not configured")

        try:
            self.client = boto3.client('rekognition', region_name=settings.REKOGNITION_REGION)
        except (BotoCoreError, NoCredentialsError) as e:
            raise RekognitionUnavailable(f"Failed to create Rekognition client: {e}")


    async def analyze_images(self, images_bytes: List[bytes]) -> Dict[str, float]:
        """
        Analyze images with Rekognition.
        Uses Custom Labels if configured, otherwise falls back to Standard Labels.

        Args:
            images_bytes: List of image bytes

        Returns:
            Dictionary with disease detections and confidence scores
        """
        # Try Custom Labels first if configured
        if settings.REKOGNITION_MODEL_ARN:
            try:
                logger.info(f"Using Custom Labels model: {settings.REKOGNITION_MODEL_ARN}")
                return self._analyze_with_custom_labels(
                    images_bytes,
                    settings.REKOGNITION_MODEL_ARN,
                    min_confidence=0.0
                )
            except Exception as e:
                logger.warning(f"Custom Labels failed: {e}")
                logger.info("Falling back to standard Rekognition labels")

        # Fall back to standard labels
        logger.info("Using standard Rekognition labels")
        return self._analyze_with_standard_labels(images_bytes)


    def _analyze_with_custom_labels(
        self,
        images_bytes: List[bytes],
        model_arn: str,
        min_confidence: float = 0.5
    ) -> Dict[str, float]:
        """Analyze with Custom Labels (trained disease model)."""
        disease_scores: Dict[str, List[float]] = {}

        for img_bytes in images_bytes[:settings.MAX_IMAGES]:
            try:
                response = self.client.detect_custom_labels(
                    ProjectVersionArn=model_arn,
                    Image={'Bytes': img_bytes},
                    MinConfidence=min_confidence * 100
                )

                for label in response.get('CustomLabels', []):
                    raw_name = label['Name']
                    confidence = label['Confidence'] / 100.0

                    # Map to KB-compatible disease name
                    disease_name = self._map_label_to_kb(raw_name)
                    disease_scores.setdefault(disease_name, []).append(confidence)

            except (ClientError, BotoCoreError) as e:
                logger.warning(f"Rekognition Custom Labels error: {e}")
                continue

        # Average scores across images
        aggregated = {
            disease: sum(scores) / len(scores)
            for disease, scores in disease_scores.items()
            if scores
        }

        logger.info(f"Custom Labels detected {len(aggregated)} diseases")
        return aggregated


    def _analyze_with_standard_labels(self, images_bytes: List[bytes]) -> Dict[str, float]:
        """Analyze with standard AWS Rekognition labels (generic features)."""
        feature_scores: Dict[str, List[float]] = {}

        for img_bytes in images_bytes[:settings.MAX_IMAGES]:
            try:
                response = self.client.detect_labels(
                    Image={'Bytes': img_bytes},
                    MaxLabels=20,
                    MinConfidence=50.0
                )

                for label in response.get('Labels', []):
                    name = label['Name'].lower()
                    confidence = label['Confidence'] / 100.0

                    # Map to disease-relevant features
                    if name in ['spot', 'stain', 'blemish', 'mark', 'spots']:
                        feature_scores.setdefault('lesion_spots_rek', []).append(confidence)
                    elif name in ['mold', 'fungus', 'mildew', 'fungi']:
                        feature_scores.setdefault('fungal_growth_rek', []).append(confidence)
                    elif name in ['discoloration', 'yellow', 'brown', 'yellowing']:
                        feature_scores.setdefault('discoloration_rek', []).append(confidence)
                    elif name in ['wilted', 'withered', 'dried', 'wilting']:
                        feature_scores.setdefault('wilting_rek', []).append(confidence)
                    elif name in ['plant', 'leaf', 'vegetation']:
                        feature_scores.setdefault('plant_detected_rek', []).append(confidence)

            except (ClientError, BotoCoreError) as e:
                logger.warning(f"Rekognition standard labels error: {e}")
                continue

        # Average scores
        aggregated = {
            feature: sum(scores) / len(scores)
            for feature, scores in feature_scores.items()
            if scores
        }

        logger.info(f"Standard labels extracted {len(aggregated)} features")
        return aggregated


    def _map_label_to_kb(self, raw_label: str) -> str:
        """Map Rekognition Custom Label name to Knowledge Base disease name."""
        normalized = raw_label.lower().strip()

        # Check direct mapping
        if normalized in REKOGNITION_TO_KB_MAPPING:
            return REKOGNITION_TO_KB_MAPPING[normalized]

        # Fallback: remove crop prefix
        if '_' in normalized:
            crop, disease = normalized.split('_', 1)
            return disease

        return normalized
