from typing import Dict, Any
import json

try:
    import boto3
except ImportError:
    boto3 = None

from app.core.config import settings


def _get_client():
    if not boto3 or not settings.BEDROCK_REGION or not settings.BEDROCK_MODEL_ID:
        raise RuntimeError("Bedrock не налаштований")
    return boto3.client("bedrock-runtime", region_name=settings.BEDROCK_REGION)


def generate_explanations(payload: Dict[str, Any]) -> Dict[str, Any]:

    client = _get_client()

    # todo
    body = json.dumps(
        {
            "inputText": (
                "Ти агроном-консультант. Коротко перепиши пояснення і план дій для кожної гіпотези.\n\n"
                + json.dumps(payload, ensure_ascii=False)
            )
        }
    )

    resp = client.invoke_model(
        modelId=settings.BEDROCK_MODEL_ID,
        accept="application/json",
        contentType="application/json",
        body=body,
    )

    raw = resp["body"].read().decode("utf-8")
    try:
        data = json.loads(raw)
        # todo 
        return data
    except Exception:
        return {"candidates": payload.get("candidates", [])}
