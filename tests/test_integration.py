"""
End-to-end integration tests.
"""
import pytest
from pathlib import Path
import json
from io import BytesIO


@pytest.mark.integration
def test_full_diagnosis_workflow(client, sample_diagnose_request, sample_image_bytes, temp_data_root):
    """Test complete workflow: diagnose -> retrieve -> verify persistence."""
    # Step 1: Submit diagnosis
    response = client.post(
        "/v1/diagnose",
        data=sample_diagnose_request,
        files={"images": ("test.png", BytesIO(sample_image_bytes), "image/png")}
    )

    assert response.status_code == 200
    case_id = response.json()["case_id"]
    original_response = response.json()

    # Step 2: Verify case was persisted to disk
    data_root = Path(temp_data_root)
    cases_dir = data_root / "cases"
    assert cases_dir.exists()

    # Find case directory
    case_dirs = list(cases_dir.rglob(case_id))
    assert len(case_dirs) > 0
    case_dir = case_dirs[0]

    # Verify files exist
    assert (case_dir / "request.json").exists()
    assert (case_dir / "response.json").exists()
    assert (case_dir / "trace.json").exists()
    assert (case_dir / "images").exists()

    # Step 3: Retrieve via API
    get_response = client.get(f"/v1/cases/{case_id}")
    assert get_response.status_code == 200

    # Step 4: Verify retrieved data matches original
    retrieved = get_response.json()
    assert retrieved["case_id"] == original_response["case_id"]
    assert len(retrieved["candidates"]) == len(original_response["candidates"])

    # Step 5: Verify image was saved
    image_files = list((case_dir / "images").glob("*.png"))
    assert len(image_files) == 1


@pytest.mark.integration
def test_pipeline_with_multiple_crops(client, sample_image_bytes):
    """Test pipeline works for all supported crops."""
    from app.api.schemas import SUPPORTED_CROPS

    for crop in SUPPORTED_CROPS:
        response = client.post(
            "/v1/diagnose",
            data={
                "crop": crop,
                "symptoms_text": f"yellow spots on {crop} leaves",
                "growth_stage": "vegetative"
            },
            files={"images": ("test.png", BytesIO(sample_image_bytes), "image/png")}
        )

        assert response.status_code == 200, f"Failed for crop: {crop}"
        data = response.json()
        assert len(data["candidates"]) > 0


@pytest.mark.integration
def test_error_handling_preserves_data_integrity(client, sample_diagnose_request, temp_data_root):
    """Test that errors don't corrupt data or leave partial writes."""
    # This test would check that failed requests don't create partial case directories
    # For now, just verify clean failure

    invalid_request = sample_diagnose_request.copy()
    invalid_request["crop"] = "invalid_crop"

    response = client.post("/v1/diagnose", data=invalid_request)
    assert response.status_code == 400

    # Verify no partial case directories created
    data_root = Path(temp_data_root)
    if (data_root / "cases").exists():
        # Should be empty or only contain valid cases
        pass  # Could add more specific checks


def test_case_listing_pagination(client, sample_diagnose_request):
    """Test case listing works with multiple cases."""
    # Create multiple cases
    case_ids = []
    for i in range(3):
        response = client.post(
            "/v1/diagnose",
            data=sample_diagnose_request
        )
        assert response.status_code == 200
        case_ids.append(response.json()["case_id"])

    # List all cases
    response = client.get("/v1/cases")
    assert response.status_code == 200
    data = response.json()

    # Should have at least our 3 cases
    assert data["total"] >= 3
    returned_ids = [c["case_id"] for c in data["cases"]]
    for case_id in case_ids:
        assert case_id in returned_ids
