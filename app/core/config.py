import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv(override=True)


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

        self.USE_REKOGNITION = os.getenv("AGRO_USE_REKOGNITION", "true").lower() == "true"  # Default to true for MVP
        self.REKOGNITION_REGION = os.getenv("AGRO_REKOGNITION_REGION")

        self.REKOGNITION_PROJECT_ARN = os.getenv("AGRO_REKOGNITION_PROJECT_ARN")
        self.REKOGNITION_MODEL_ARN = os.getenv("AGRO_REKOGNITION_MODEL_ARN")

        # LLM / Bedrock
        self.LLM_MODE = os.getenv("AGRO_LLM_MODE", "stub").lower()
        self.BEDROCK_REGION = os.getenv("AGRO_BEDROCK_REGION")
        self.BEDROCK_MODEL_ID = os.getenv("AGRO_BEDROCK_MODEL_ID")

        # Database
        self.DATABASE_URL = os.getenv("DATABASE_URL")  # Full connection string
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "agrodiag")
        self.DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
        self.USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

        # S3 for image storage (optional)
        self.USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
        self.S3_BUCKET = os.getenv("S3_BUCKET", "agrodiag-images")
        self.S3_REGION = os.getenv("S3_REGION", "us-east-1")
        self.S3_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
        self.S3_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

        # API Authentication
        self.REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
        self.API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
