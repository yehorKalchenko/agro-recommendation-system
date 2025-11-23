import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        self.DATA_ROOT = os.getenv("AGRO_DATA_ROOT", os.getenv("DATA_ROOT", "./data"))

        self.MAX_IMAGES = int(os.getenv("AGRO_MAX_IMAGES", os.getenv("MAX_IMAGES", "4")))
        self.MAX_IMAGE_MB = int(os.getenv("AGRO_MAX_IMAGE_MB", os.getenv("MAX_IMAGE_MB", "5")))
        self.ALLOWED_MIME = (
            os.getenv(
                "AGRO_ALLOWED_MIME",
                os.getenv("ALLOWED_MIME", "image/jpeg,image/png,image/webp"),
            )
            .strip()
            .split(",")
        )

        self.RAG_MODE = os.getenv("AGRO_RAG_MODE", os.getenv("RAG_MODE", "tfidf")).lower()
        self.SCORING_ALPHA = float(os.getenv("AGRO_SCORING_ALPHA", os.getenv("SCORING_ALPHA", "0.6")))

        self.USE_REKOGNITION = os.getenv("AGRO_USE_REKOGNITION", "false").lower() == "true"
        self.REKOGNITION_REGION = os.getenv("AGRO_REKOGNITION_REGION")

        self.REKOGNITION_PROJECT_ARN = os.getenv("AGRO_REKOGNITION_PROJECT_ARN")
        self.REKOGNITION_MODEL_ARN = os.getenv("AGRO_REKOGNITION_MODEL_ARN")

        # LLM / Bedrock
        self.LLM_MODE = os.getenv("AGRO_LLM_MODE", "stub").lower()
        self.BEDROCK_REGION = os.getenv("AGRO_BEDROCK_REGION")
        self.BEDROCK_MODEL_ID = os.getenv("AGRO_BEDROCK_MODEL_ID")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
