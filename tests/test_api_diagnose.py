"""
Tests for POST /v1/diagnose endpoint.
"""
import pytest
from io import BytesIO


def test_health_endpoint(client):
    """Sanity check: health endpoint works."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_diagnose_without_images_success(client, sample_diagnose_request, temp_data_root):
    """Test POST /v1/diagnose without images (text-only diagnosis)."""
    response = client.post(
        "/v1/diagnose",
        data=sample_diagnose_request
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "case_id" in data
    assert "candidates" in data
    assert "plan" in data
    assert "disclaimers" in data

    # Should have at least one candidate
    assert len(data["candidates"]) > 0

    # Validate candidate structure
    candidate = data["candidates"][0]
    assert "disease" in candidate
    assert "score" in candidate
    assert "rationale" in candidate
    assert 0 <= candidate["score"] <= 1

    # Validate plan structure
    plan = data["plan"]
    assert "diagnostics" in plan
    assert "agronomy" in plan
    assert "chemical" in plan
    assert "bio" in plan


def test_diagnose_with_one_image_success(client, sample_diagnose_request, sample_image_bytes):
    """Test POST /v1/diagnose with one valid image."""
    response = client.post(
        "/v1/diagnose",
        data=sample_diagnose_request,
        files={"images": ("test.png", BytesIO(sample_image_bytes), "image/png")}
    )

    assert response.status_code == 200
    data = response.json()

    assert "case_id" in data
    assert len(data["candidates"]) > 0

    # Debug info should show CV processing occurred
    if "debug" in data:
        assert "timings" in data["debug"]
        assert "cv" in data["debug"]["timings"]


def test_diagnose_with_multiple_images(client, sample_diagnose_request, sample_image_bytes):
    """Test POST /v1/diagnose with multiple images (within limit)."""
    # AGRO_MAX_IMAGES is set to 3 in conftest
    files = [
        ("images", ("test1.png", BytesIO(sample_image_bytes), "image/png")),
        ("images", ("test2.png", BytesIO(sample_image_bytes), "image/png")),
    ]

    response = client.post(
        "/v1/diagnose",
        data=sample_diagnose_request,
        files=files
    )

    assert response.status_code == 200


def test_diagnose_invalid_mime_type(client, sample_diagnose_request):
    """Test rejection of invalid MIME type."""
    response = client.post(
        "/v1/diagnose",
        data=sample_diagnose_request,
        files={"images": ("test.txt", BytesIO(b"text file"), "text/plain")}
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_diagnose_too_many_images(client, sample_diagnose_request, sample_image_bytes):
    """Test rejection when exceeding MAX_IMAGES limit."""
    # MAX_IMAGES is 3 in test config, send 4
    files = [
        ("images", (f"test{i}.png", BytesIO(sample_image_bytes), "image/png"))
        for i in range(4)
    ]

    response = client.post(
        "/v1/diagnose",
        data=sample_diagnose_request,
        files=files
    )

    assert response.status_code == 400
    assert "Too many files" in response.json()["detail"]


def test_diagnose_oversized_image(client, sample_diagnose_request, oversized_image_bytes):
    """Test rejection of image exceeding MAX_IMAGE_MB."""
    response = client.post(
        "/v1/diagnose",
        data=sample_diagnose_request,
        files={"images": ("huge.png", BytesIO(oversized_image_bytes), "image/png")}
    )

    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"].lower()


def test_diagnose_missing_required_field(client):
    """Test validation error when required field missing."""
    response = client.post(
        "/v1/diagnose",
        data={
            "crop": "tomato",
            # Missing symptoms_text
        }
    )

    assert response.status_code == 422  # Validation error


def test_diagnose_invalid_crop(client):
    """Test validation error for unsupported crop."""
    response = client.post(
        "/v1/diagnose",
        data={
            "crop": "banana",  # Not in SUPPORTED_CROPS
            "symptoms_text": "yellow spots on leaves"
        }
    )

    assert response.status_code == 400
    assert "Unsupported crop" in response.json()["detail"]


def test_diagnose_symptoms_too_short(client):
    """Test validation error for symptoms text too short."""
    response = client.post(
        "/v1/diagnose",
        data={
            "crop": "tomato",
            "symptoms_text": "abc"  # Less than 5 characters
        }
    )

    assert response.status_code == 422
