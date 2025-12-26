"""
Rules Engine Helper for filtering and scoring disease candidates.
Extracted from rules/engine.py for cleaner architecture.
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class RulesHelper:
    """
    Helper class for applying rule-based filters and scoring adjustments.

    """

    @staticmethod
    def apply_rules(
        crop: str,
        growth_stage: str,
        features: Dict,
        kb_cards: List[Dict]
    ) -> List[Dict]:
        """
        Apply rule-based filters and scoring adjustments.

        Args:
            crop: Crop name (e.g., "tomato")
            growth_stage: Growth stage (e.g., "fruiting")
            features: Visual features from CVService
            kb_cards: Disease cards from RAGRetriever

        Returns:
            Filtered and scored disease cards
        """
        filtered_cards = []

        for card in kb_cards:
            # ─────────────────────────────────────────────────────
            # RULE 1: Crop Filter
            # ─────────────────────────────────────────────────────
            if crop not in card.get("crops_supported", []):
                continue  # Skip diseases not supported for this crop

            # ─────────────────────────────────────────────────────
            # RULE 2: Growth Stage Penalty
            # ─────────────────────────────────────────────────────
            score = card.get("_score", 0.0)
            stage_window = card.get("stage_window", [])

            if growth_stage and stage_window and growth_stage not in stage_window:
                score *= 0.8  # 20% penalty

            # ─────────────────────────────────────────────────────
            # RULE 3: Visual Pattern Bonus
            # ─────────────────────────────────────────────────────
            visual_patterns = card.get("visual_patterns", [])
            patterns_text = " ".join(visual_patterns).lower()

            # Powdery mildew bonus
            if features.get("white_powder") and "powdery" in patterns_text:
                score += 0.1

            # Water-soaked lesions bonus
            if features.get("water_soaked") and "water-soaked" in patterns_text:
                score += 0.1

            # ─────────────────────────────────────────────────────
            # RULE 4: Normalization
            # ─────────────────────────────────────────────────────
            card["_rule_score"] = min(score, 1.0)
            filtered_cards.append(card)

        # Sort by rule score (descending)
        return sorted(filtered_cards, key=lambda x: x["_rule_score"], reverse=True)
