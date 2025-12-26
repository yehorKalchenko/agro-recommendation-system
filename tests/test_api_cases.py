"""
Tests for GET /v1/cases/* endpoints.
"""
import pytest
import json
from pathlib import Path


@pytest.fixture
def created_case(client, sample_diagnose_request, temp_data_root):
    """Create a case and return its case_id."""
    response = client.post("/v1/diagnose", data=sample_diagnose_request)
    assert response.status_code == 200
    case_id = response.json()["case_id"]
    return case_id, response.json()


def test_get_case_success(client, created_case):
    """Test GET /v1/cases/{case_id} for existing case."""
    case_id, original_response = created_case

    response = client.get(f"/v1/cases/{case_id}")

    assert response.status_code == 200
    data = response.json()

    # Should match original response
    assert data["case_id"] == case_id
    assert data["candidates"] == original_response["candidates"]
    assert data["plan"] == original_response["plan"]


def test_get_case_not_found(client):
    """Test GET /v1/cases/{case_id} for non-existent case."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/v1/cases/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_case_invalid_id_format(client):
    """Test GET /v1/cases/{case_id} with invalid ID format."""
    invalid_ids = [
        "",  # Empty
        "../../../etc/passwd",  # Path traversal attempt
        "invalid@chars#here",  # Invalid characters
        "x" * 200,  # Too long
    ]

    for invalid_id in invalid_ids:
        response = client.get(f"/v1/cases/{invalid_id}")
        assert response.status_code in [400, 404]


def test_list_cases_empty(client, temp_data_root):
    """Test GET /v1/cases when no cases exist."""
    response = client.get("/v1/cases")

    assert response.status_code == 200
    data = response.json()
    assert data["cases"] == []
    assert data["total"] == 0


def test_list_cases_with_data(client, created_case):
    """Test GET /v1/cases returns created cases."""
    case_id, _ = created_case

    response = client.get("/v1/cases")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] > 0
    assert len(data["cases"]) > 0

    # Find our case in the list
    case_ids = [c["case_id"] for c in data["cases"]]
    assert case_id in case_ids


def test_list_cases_with_date_filter(client, created_case):
    """Test GET /v1/cases?date=YYYY-MM-DD."""
    from datetime import date

    case_id, _ = created_case
    today = date.today().isoformat()

    response = client.get(f"/v1/cases?date={today}")

    assert response.status_code == 200
    data = response.json()

    # Should include today's case
    assert data["total"] > 0
    assert case_id in [c["case_id"] for c in data["cases"]]


def test_list_cases_invalid_date_format(client):
    """Test GET /v1/cases with invalid date format."""
    response = client.get("/v1/cases?date=invalid-date")

    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]


def test_list_cases_with_limit(client, created_case):
    """Test GET /v1/cases respects limit parameter."""
    response = client.get("/v1/cases?limit=1")

    assert response.status_code == 200
    data = response.json()

    # Should not exceed limit
    assert len(data["cases"]) <= 1
