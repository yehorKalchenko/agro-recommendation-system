"""
LLM Client Service for ranking and reasoning about disease candidates.

Combines:
- Stub ranking (weighted scoring)
- AWS Bedrock integration (optional, for enhanced explanations)
"""
from typing import List, Dict, Optional
import logging

from app.api.schemas import DiagnoseRequest
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM Client Service for ranking disease candidates and generating rationales.

    This service acts as a facade that coordinates:
    1. Stub ranking (fast, rule-based scoring)
    2. AWS Bedrock enrichment (optional, for enhanced explanations)

    Usage:
        llm_client = LLMClient()
        ranked = await llm_client.rank_and_reason(req, candidates)
    """

    def __init__(self):
        """Initialize LLM Client with optional Bedrock helper."""
        self.llm_mode = settings.LLM_MODE
        self.scoring_alpha = settings.SCORING_ALPHA
        self._bedrock_helper = None

        if self.llm_mode == "bedrock":
            try:
                from app.services.helpers.bedrock_helper import BedrockHelper
                self._bedrock_helper = BedrockHelper()
                logger.info("LLMClient initialized with Bedrock support")
            except ImportError:
                logger.warning("Bedrock helper not available, using stub mode only")
                self.llm_mode = "stub"


    async def rank_and_reason(
        self,
        req: DiagnoseRequest,
        candidates: List[Dict],
        use_bedrock: Optional[bool] = None
    ) -> List[Dict]:
        """
        Rank disease candidates and generate rationales.

        Args:
            req: Diagnosis request with symptoms and context
            candidates: List of disease cards from RAGRetriever
            use_bedrock: Override .env setting for Bedrock LLM (True/False/None)

        Returns:
            List of ranked candidates with scores and rationales

        """
        # Determine if Bedrock should be used (parameter overrides .env)
        should_use_bedrock = use_bedrock if use_bedrock is not None else (self.llm_mode == "bedrock")

        logger.info(f"Ranking {len(candidates)} candidates (bedrock={should_use_bedrock})")

        # Stage 1: Stub ranking (always runs)
        ranked = self._rank_stub(req, candidates)

        # Stage 2: Bedrock enrichment (optional)
        if should_use_bedrock and self._bedrock_helper:
            try:
                ranked = await self._enrich_with_bedrock(req, ranked)
                logger.info("Successfully enriched candidates with Bedrock LLM")
            except Exception as e:
                logger.warning(f"Bedrock enrichment failed: {e}")
                # Continue with stub results

        return ranked


    def _rank_stub(
        self,
        req: DiagnoseRequest,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Stub ranking using weighted scoring.

        Combines:
        - _rule_score (from Rules Engine)
        - _score (from RAG Retriever)

        Formula: final_score = alpha * rule_score + (1 - alpha) * rag_score
        """
        alpha = self.scoring_alpha
        text = (req.symptoms_text or "").lower()

        result = []

        for card in candidates:
            # Get scores from previous stages
            s_rules = float(card.get("_rule_score", 0.0))
            s_rag = float(card.get("_score", 0.0))

            # Combined score (weighted average)
            score = alpha * s_rules + (1.0 - alpha) * s_rag

            # Generate simple rationale
            rationale_bits = []

            # Check symptom matching
            matched_symptoms = []
            for symptom in card.get("symptoms", []):
                if any(word in text for word in symptom.lower().split()):
                    matched_symptoms.append(symptom)

            if matched_symptoms:
                rationale_bits.append(f"Збіг симптомів: {', '.join(matched_symptoms[:3])}")

            # Check visual patterns
            visual_patterns = card.get("visual_patterns", [])
            patterns_text = " ".join(visual_patterns).lower()

            if any(k in patterns_text for k in ["powder", "мучнист", "downy", "пероноспор", "water-soaked"]):
                rationale_bits.append("Візуальні ознаки відповідають опису в KB")

            # Check growth stage
            if req.growth_stage and card.get("stage_window"):
                rationale_bits.append("Стадія росту врахована")

            rationale = "; ".join(rationale_bits) or "Гіпотеза на основі близькості симптомів у KB"

            result.append({
                "name": card["name"],
                "score": round(min(max(score, 0.0), 1.0), 3),
                "rationale": rationale,
                "kb_refs": [{"id": card["id"], "name": card["name"]}],
                "actions": card.get("actions", {}),
            })

        # Sort by score (descending)
        return sorted(result, key=lambda x: x["score"], reverse=True)


    async def _enrich_with_bedrock(
        self,
        req: DiagnoseRequest,
        ranked: List[Dict]
    ) -> List[Dict]:
        """
        Enrich candidates with AWS Bedrock LLM-generated explanations.

        Args:
            req: Diagnosis request
            ranked: Ranked candidates from stub

        Returns:
            Enriched candidates with improved rationales
        """
        if not ranked or not self._bedrock_helper:
            return ranked

        # Build payload for LLM
        payload = {
            "symptoms_text": req.symptoms_text,
            "crop": req.crop,
            "growth_stage": req.growth_stage,
            "candidates": [
                {
                    "name": c["name"],
                    "score": c["score"],
                    "rationale": c["rationale"],
                    "actions": c.get("actions", {}),
                }
                for c in ranked
            ],
        }

        try:
            # Call Bedrock helper
            enriched_payload = await self._bedrock_helper.generate_explanations(payload)

            # Merge enriched explanations back into ranked candidates
            for candidate, enriched in zip(ranked, enriched_payload.get("candidates", [])):
                if "explanation" in enriched:
                    candidate["rationale"] = enriched["explanation"]

                if "key_indicators" in enriched:
                    candidate["key_indicators"] = enriched["key_indicators"]

                if "next_steps" in enriched:
                    if "actions" not in candidate:
                        candidate["actions"] = {}
                    candidate["actions"]["next_steps"] = enriched["next_steps"]

        except Exception as e:
            logger.error(f"Bedrock enrichment error: {e}")
            # Return original ranked results

        return ranked
