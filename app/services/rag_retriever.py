"""
RAG (Retrieval-Augmented Generation) Retriever Service.

Retrieves relevant disease candidates from the knowledge base using:
- TF-IDF-like keyword matching
- Visual pattern matching
- Rekognition confidence boosting
"""
import os
import glob
import yaml
import math
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Knowledge base root directory
KB_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "kb")

# Keywords for symptom matching (Ukrainian and English)
KEYWORDS = [
    "плями", "наліт", "жовт", "в'ян", "водянист", "смуги",
    "пустули", "білий", "чорн", "мозаїк", "spots", "powder",
    "yellow", "wilting", "water-soaked", "streaks"
]


class RAGRetriever:
    """
    RAG Retriever Service for searching the knowledge base.

    This service searches through YAML-based disease profiles and scores
    them based on symptom matching, visual patterns, and ML detections.

    Usage:
        retriever = RAGRetriever()
        candidates = await retriever.retrieve(crop, symptoms_text, features)
    """

    def __init__(self):
        """Initialize RAG Retriever."""
        self.kb_root = KB_ROOT
        logger.info(f"RAGRetriever initialized with KB_ROOT: {self.kb_root}")


    async def retrieve(
        self,
        crop: str,
        symptoms_text: str,
        features: Dict[str, float]
    ) -> List[Dict]:
        """
        Retrieve and rank disease candidates from knowledge base.

        Args:
            crop: Crop name (e.g., "tomato", "potato")
            symptoms_text: User-provided symptom description
            features: Extracted visual features from CVService

        Returns:
            List of disease cards sorted by relevance score (descending)

        Example:
            [
                {
                    "id": "kb:tomato:late_blight",
                    "name": "Late blight (фітофтороз)",
                    "_score": 0.999,
                    "symptoms": [...],
                    "actions": {...},
                    ...
                },
                ...
            ]
        """
        logger.info(f"Retrieving KB for crop={crop}, features={len(features)} keys")

        # Load disease cards for the specified crop
        cards = self._load_kb_cards(crop)

        if not cards:
            logger.warning(f"No disease cards found for crop: {crop}")
            return []

        # Score each card
        for card in cards:
            card["_score"] = self._score_card(symptoms_text, features, card)

        # Sort by score (descending)
        sorted_cards = sorted(cards, key=lambda x: x["_score"], reverse=True)

        logger.info(f"Retrieved {len(sorted_cards)} candidates, top score: {sorted_cards[0]['_score']:.3f}")
        return sorted_cards


    def _load_kb_cards(self, crop: str) -> List[Dict]:
        """
        Load all disease YAML files for a given crop.

        Args:
            crop: Crop name (e.g., "tomato")

        Returns:
            List of disease dictionaries
        """
        pattern = os.path.join(self.kb_root, crop, "*.yaml")
        cards = []

        for path in glob.glob(pattern):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                    # Generate unique ID
                    disease_id = os.path.basename(path).replace('.yaml', '')
                    data["id"] = f"kb:{crop}:{disease_id}"
                    data["_disease_id"] = disease_id  # For Rekognition matching

                    cards.append(data)

            except Exception as e:
                logger.warning(f"Failed to load KB card {path}: {e}")
                continue

        logger.debug(f"Loaded {len(cards)} disease cards for crop: {crop}")
        return cards


    def _score_card(
        self,
        symptoms_text: str,
        features: Dict[str, float],
        card: Dict
    ) -> float:
        """
        Score a disease card based on symptom matching and visual features.

        Scoring algorithm:
        1. Keyword matching: +1 for each matched keyword
        2. Visual pattern bonus: +2 for specific patterns (powdery, downy mildew)
        3. Rekognition boost: +4 * confidence (MAJOR factor!)
        4. Sigmoid normalization: 1 - exp(-base)

        Args:
            symptoms_text: User symptom description
            features: Visual features from CVService
            card: Disease card dictionary

        Returns:
            Confidence score (0.0-1.0)
        """
        text_lower = symptoms_text.lower()
        base_score = 0.0

        # ─────────────────────────────────────────────────────
        # 1. KEYWORD MATCHING
        # ─────────────────────────────────────────────────────
        card_symptoms = card.get("symptoms", [])

        for keyword in KEYWORDS:
            if keyword in text_lower:
                # Check if this keyword appears in card's symptom descriptions
                for symptom in card_symptoms:
                    if keyword in symptom.lower():
                        base_score += 1
                        break  # Count each keyword only once

        # ─────────────────────────────────────────────────────
        # 2. VISUAL PATTERN BONUS
        # ─────────────────────────────────────────────────────
        visual_patterns = card.get("visual_patterns", [])
        patterns_text = " ".join(visual_patterns).lower()

        # Powdery mildew (білий наліт)
        if features.get("white_powder") and ("powder" in patterns_text or "мучнист" in patterns_text):
            base_score += 2

        # Downy mildew (пероноспороз)
        if features.get("downy_mildew") and ("downy" in patterns_text or "пероноспор" in patterns_text):
            base_score += 2

        # ─────────────────────────────────────────────────────
        # 3. REKOGNITION BOOST (Critical!)
        # ─────────────────────────────────────────────────────
        # If Rekognition detected this specific disease, boost score significantly
        disease_id = card.get("_disease_id", "")

        if disease_id:
            rekognition_confidence = features.get(disease_id, 0.0)

            if rekognition_confidence > 0:
                # Strong boost: multiply confidence by 4
                # Example: 0.92 confidence → +3.68 to base_score
                base_score += rekognition_confidence * 4

                logger.debug(f"Rekognition boost for {disease_id}: {rekognition_confidence:.2f} → +{rekognition_confidence * 4:.2f}")

        # ─────────────────────────────────────────────────────
        # 4. SIGMOID NORMALIZATION
        # ─────────────────────────────────────────────────────
        # Convert unbounded score to [0, 1] range
        normalized_score = 1 - math.exp(-base_score)

        return normalized_score
