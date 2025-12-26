"""
Computer Vision Service for plant disease feature extraction.

Combines:
- Text-based symptom analysis
- Image-based feature extraction (Pillow)
- AWS Rekognition integration (optional)
"""
from typing import List, Dict, Optional
from fastapi import UploadFile
from io import BytesIO
from PIL import Image, ImageFilter
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class CVService:
    """
    Computer Vision Service for extracting visual features from images and text.

    This service acts as a facade that coordinates:
    1. Text-based keyword extraction
    2. Pillow-based image analysis (pixel statistics, edge detection)
    3. AWS Rekognition integration (if enabled)

    Usage:
        cv_service = CVService()
        features = await cv_service.extract_features(images, symptoms_text, images_bytes)
    """

    def __init__(self):
        """Initialize CV Service with optional Rekognition client."""
        self.use_rekognition = settings.USE_REKOGNITION
        self._rekognition_client = None

        if self.use_rekognition:
            try:
                from app.services.helpers.rekognition_helper import RekognitionHelper
                self._rekognition_helper = RekognitionHelper()
                logger.info("CVService initialized with Rekognition support")
            except ImportError:
                logger.warning("Rekognition helper not available, using Pillow only")
                self.use_rekognition = False


    async def extract_features(
        self,
        images: List[UploadFile],
        symptoms_text: str,
        images_bytes: Optional[List[bytes]] = None,
        use_rekognition: Optional[bool] = None
    ) -> Dict[str, float]:
        """
        Extract visual features from images and text.

        Args:
            images: List of uploaded image files
            symptoms_text: User-provided symptom description
            images_bytes: Pre-read image bytes (optional, for performance)
            use_rekognition: Override .env setting for Rekognition (True/False/None)

        Returns:
            Dictionary mapping feature names to confidence scores (0.0-1.0)

        Example:
            {
                "lesion_spots": 1.0,
                "white_powder": 0.0,
                "water_soaked": 1.0,
                "water_soaked_img": 1.0,
                "lesion_spots_img": 1.0,
                "late_blight": 0.92,  # from Rekognition
                ...
            }
        """
        logger.info(f"Extracting features from {len(images_bytes or [])} images")

        # Extract text-based features
        text_features = self._extract_text_features(symptoms_text)

        # Extract image-based features
        image_features = {}
        if images_bytes:
            image_features = self._extract_image_features(images_bytes)

        # Merge features
        features = {**text_features, **image_features}

        # Determine if Rekognition should be used (parameter overrides .env)
        should_use_rekognition = use_rekognition if use_rekognition is not None else self.use_rekognition

        # Add Rekognition features if enabled
        if should_use_rekognition and images_bytes and self._rekognition_helper:
            try:
                rek_features = await self._extract_rekognition_features(images_bytes)
                features.update(rek_features)
                logger.info(f"Added {len(rek_features)} Rekognition features")
            except Exception as e:
                logger.warning(f"Rekognition extraction failed: {e}")

        return features


    def _extract_text_features(self, symptoms_text: str) -> Dict[str, float]:
        """
        Extract features from text using keyword matching.

        Args:
            symptoms_text: User-provided symptom description

        Returns:
            Dictionary of binary features (0.0 or 1.0)
        """
        text = (symptoms_text or "").lower()

        features = {
            "lesion_spots": 1.0 if any(k in text for k in ["плями", "плям", "пятна", "spots", "lesions"]) else 0.0,
            "white_powder": 1.0 if any(k in text for k in ["білий наліт", "мучнист", "powdery"]) else 0.0,
            "downy_mildew": 1.0 if any(k in text for k in ["пероноспор", "несправж", "downy"]) else 0.0,
            "wilting": 1.0 if any(k in text for k in ["в'ян", "вян", "wilting"]) else 0.0,
            "yellowing": 1.0 if any(k in text for k in ["жовт", "yellow"]) else 0.0,
            "black_spots": 1.0 if any(k in text for k in ["чорн", "black spot"]) else 0.0,
            "water_soaked": 1.0 if any(k in text for k in ["водянист", "water-soaked"]) else 0.0,
        }

        return features


    def _extract_image_features(self, images_bytes: List[bytes]) -> Dict[str, float]:
        """
        Extract features from images using Pillow (pixel analysis, edge detection).

        Args:
            images_bytes: List of image bytes

        Returns:
            Dictionary of image-based features with debug metrics
        """
        if not images_bytes:
            return {}

        white_like_sum = 0.0
        very_dark_sum = 0.0
        edges_sum = 0.0
        valid_images = 0

        for img_bytes in images_bytes:
            try:
                im = Image.open(BytesIO(img_bytes)).convert("RGB")
                im = im.resize((64, 64))  # Resize for performance
            except Exception:
                logger.warning("Failed to process image with Pillow")
                continue

            px = im.load()
            w, h = im.size
            total = w * h
            white_cnt, dark_cnt = 0, 0

            # Pixel-by-pixel analysis
            for y in range(h):
                for x in range(w):
                    r, g, b = px[x, y]
                    v = max(r, g, b) / 255.0
                    near_gray = (abs(r - g) < 18 and abs(g - b) < 18 and abs(r - b) < 18)

                    # White/gray pixels (powdery mildew indicator)
                    if near_gray and v > 0.75:
                        white_cnt += 1

                    # Very dark pixels (water-soaked lesions)
                    if v < 0.18:
                        dark_cnt += 1

            # Edge detection (lesion spots indicator)
            edges = im.filter(ImageFilter.FIND_EDGES).convert("L")
            edges_val = sum(edges.getdata()) / (255.0 * total)

            white_like_sum += white_cnt / total
            very_dark_sum += dark_cnt / total
            edges_sum += edges_val
            valid_images += 1

        if valid_images == 0:
            return {}

        # Average across all images
        avg_white = white_like_sum / valid_images
        avg_dark = very_dark_sum / valid_images
        avg_edges = edges_sum / valid_images

        return {
            "white_powder_img": 1.0 if avg_white > 0.35 else 0.0,
            "water_soaked_img": 1.0 if avg_dark > 0.15 else 0.0,
            "lesion_spots_img": 1.0 if avg_edges > 0.25 else 0.0,
            "_white_like": round(avg_white, 3),
            "_very_dark": round(avg_dark, 3),
            "_edges_mean": round(avg_edges, 3),
        }


    async def _extract_rekognition_features(self, images_bytes: List[bytes]) -> Dict[str, float]:
        """
        Extract features using AWS Rekognition (Custom Labels or Standard Labels).

        Args:
            images_bytes: List of image bytes

        Returns:
            Dictionary of disease detections and visual features from Rekognition
        """
        if not self._rekognition_helper:
            return {}

        return await self._rekognition_helper.analyze_images(images_bytes)
