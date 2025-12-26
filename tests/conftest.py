"""
Pytest fixtures for AgroDiag tests.
"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Set test environment variables BEFORE importing app
os.environ['AGRO_DATA_ROOT'] = tempfile.mkdtemp()
os.environ['AGRO_MAX_IMAGES'] = '3'
os.environ['AGRO_MAX_IMAGE_MB'] = '2'
os.environ['AGRO_USE_REKOGNITION'] = 'false'
os.environ['AGRO_LLM_MODE'] = 'stub'

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="function")
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
def temp_data_root(monkeypatch):
    """
    Create temporary data directory for testing.
    Automatically cleaned up after test.
    """
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("AGRO_DATA_ROOT", temp_dir)

    # Reload settings to pick up new env var
    from app.core import config
    config.get_settings.cache_clear()

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_diagnose_request():
    """Sample diagnosis request payload."""
    return {
        "crop": "tomato",
        "symptoms_text": "brown water-soaked spots on leaves with white coating underneath",
        "growth_stage": "vegetative",
        "lat": 50.4501,
        "lon": 30.5234
    }


@pytest.fixture
def sample_image_bytes():
    """Generate a minimal valid PNG image for testing."""
    from io import BytesIO
    from PIL import Image

    # Create 100x100 red square
    img = Image.new('RGB', (100, 100), color='red')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


@pytest.fixture
def invalid_image_bytes():
    """Invalid image data for error testing."""
    return b"not a valid image"


@pytest.fixture
def oversized_image_bytes():
    """Generate image larger than MAX_IMAGE_MB for testing."""
    from io import BytesIO
    from PIL import Image

    # Create large image (should exceed 2MB test limit)
    img = Image.new('RGB', (3000, 3000), color='blue')
    buf = BytesIO()
    img.save(buf, format='PNG', compress_level=0)
    buf.seek(0)
    return buf.read()
