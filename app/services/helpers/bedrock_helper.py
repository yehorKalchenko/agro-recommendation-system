"""
AWS Bedrock Helper for LLM-enhanced disease explanations.
Extracted from llm/bedrock_client.py for cleaner architecture.
"""
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

try:
    import aioboto3
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.info("AWS SDK not available - Bedrock unavailable")

from app.core.config import settings


class BedrockUnavailable(Exception):
    """Raised when Bedrock service is unavailable or misconfigured."""
    pass


class BedrockHelper:
    """Helper class for AWS Bedrock operations."""

    def __init__(self):
        """Initialize Bedrock client."""
        if not BOTO3_AVAILABLE:
            raise BedrockUnavailable("boto3/aioboto3 not installed")

        if not settings.BEDROCK_REGION or not settings.BEDROCK_MODEL_ID:
            raise BedrockUnavailable("Bedrock not configured (region or model_id missing)")


    async def generate_explanations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich disease candidates with LLM-generated explanations.

        Args:
            payload: Dict containing symptoms_text, crop, growth_stage, and candidates

        Returns:
            Enhanced payload with improved rationales and recommendations
        """
        try:
            prompt = self._build_prompt(payload)
            enriched = await self._call_bedrock_async(prompt)

            logger.info(f"Successfully enriched {len(enriched.get('candidates', []))} candidates")
            return enriched

        except Exception as e:
            logger.warning(f"Bedrock enrichment failed: {e}")
            # Return original payload on failure
            return payload


    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        """Build prompt for disease diagnosis enhancement."""
        crop = payload.get('crop', 'unknown')
        growth_stage = payload.get('growth_stage', 'unknown')
        symptoms = payload.get('symptoms_text', '')
        candidates = payload.get('candidates', [])

        # Build candidate summaries
        candidate_text = ""
        for i, c in enumerate(candidates, 1):
            candidate_text += f"\n{i}. {c['name']} (confidence: {c['score']:.2f})"
            candidate_text += f"\n   Current explanation: {c.get('rationale', 'N/A')}"

        prompt = f"""You are an expert agricultural consultant specializing in plant diseases.

Context:
- Crop: {crop}
- Growth stage: {growth_stage}
- Farmer's observations: {symptoms}

Current disease hypotheses:{candidate_text}

Your task:
For each hypothesis, provide:
1. Clear explanation - Why this disease is likely given the symptoms (2-3 sentences, in Ukrainian)
2. Key indicators - Specific visual signs to confirm the diagnosis
3. Next steps - Immediate actions the farmer should take

Keep explanations practical and accessible to farmers. Use simple language.
Focus on actionable insights.

Return your response as JSON with this structure:
{{
  "candidates": [
    {{
      "name": "disease name",
      "explanation": "improved Ukrainian explanation",
      "key_indicators": ["indicator 1", "indicator 2"],
      "next_steps": ["step 1", "step 2"]
    }}
  ]
}}"""

        return prompt


    async def _call_bedrock_async(self, prompt: str) -> Dict[str, Any]:
        """Async call to AWS Bedrock."""
        session = aioboto3.Session()

        async with session.client("bedrock-runtime", region_name=settings.BEDROCK_REGION) as client:
            # Determine body format based on model ID
            model_id = settings.BEDROCK_MODEL_ID.lower()

            if "claude" in model_id:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}]
                })
            elif "nova" in model_id:
                # Amazon Nova models use different format
                body = json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {
                        "max_new_tokens": 2000,
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                })
            elif "titan" in model_id:
                body = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 2000,
                        "temperature": 0.3,
                        "topP": 0.9,
                        "stopSequences": []
                    }
                })
            else:
                # Default to Titan format
                body = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 2000,
                        "temperature": 0.3,
                        "topP": 0.9
                    }
                })

            try:
                response = await client.invoke_model(
                    modelId=settings.BEDROCK_MODEL_ID,
                    accept="application/json",
                    contentType="application/json",
                    body=body
                )

                raw = await response["body"].read()
                data = json.loads(raw.decode("utf-8"))

                # Extract text based on response format
                text = ""
                if "output" in data and "message" in data["output"]:  # Nova format
                    content = data["output"]["message"].get("content", [])
                    if content and len(content) > 0:
                        text = content[0].get("text", "")
                elif "results" in data:  # Titan format
                    text = data["results"][0]["outputText"]
                elif "generation" in data:  # Llama format
                    text = data["generation"]
                elif "content" in data:  # Claude format
                    content = data.get("content", [])
                    if content and len(content) > 0:
                        text = content[0].get("text", "")
                else:
                    text = data.get("text", data.get("output", str(data)))

                # Parse JSON from response
                logger.debug(f"Raw Bedrock response (first 500 chars): {text[:500]}")

                # Try different extraction methods
                json_text = None

                # Method 1: Check for markdown code blocks
                if "```json" in text:
                    json_start = text.find("```json") + 7
                    json_end = text.find("```", json_start)
                    if json_end > json_start:
                        json_text = text[json_start:json_end].strip()

                # Method 2: Check for plain code blocks
                elif "```" in text:
                    json_start = text.find("```") + 3
                    json_end = text.find("```", json_start)
                    if json_end > json_start:
                        json_text = text[json_start:json_end].strip()

                # Method 3: Find JSON object with balanced braces
                if not json_text:
                    # Find first { and last }
                    first_brace = text.find('{')
                    last_brace = text.rfind('}')
                    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                        json_text = text[first_brace:last_brace + 1]

                # Fallback: use entire text
                if not json_text:
                    json_text = text

                json_text = json_text.strip()

                try:
                    return json.loads(json_text)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {e}")
                    logger.error(f"Failed to parse: {json_text[:500]}")
                    # Return original payload on parse failure
                    raise

            except (ClientError, json.JSONDecodeError) as e:
                logger.error(f"Bedrock API error: {e}")
                raise
