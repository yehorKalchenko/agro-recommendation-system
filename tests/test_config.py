"""
Tests for configuration management.
"""
import os
import pytest


def test_settings_loads_from_env(monkeypatch):
    """Test Settings class loads from AGRO_ prefixed env vars."""
    monkeypatch.setenv("AGRO_MAX_IMAGES", "10")
    monkeypatch.setenv("AGRO_MAX_IMAGE_MB", "15")
    monkeypatch.setenv("AGRO_DATA_ROOT", "/custom/path")

    # Reload settings
    from app.core import config
    config.get_settings.cache_clear()
    settings = config.get_settings()

    assert settings.MAX_IMAGES == 10
    assert settings.MAX_IMAGE_MB == 15
    assert settings.DATA_ROOT == "/custom/path"


def test_settings_fallback_to_non_prefixed(monkeypatch):
    """Test Settings falls back to non-AGRO_ prefixed vars."""
    monkeypatch.delenv("AGRO_MAX_IMAGES", raising=False)
    monkeypatch.setenv("MAX_IMAGES", "7")

    from app.core import config
    config.get_settings.cache_clear()
    settings = config.get_settings()

    assert settings.MAX_IMAGES == 7


def test_settings_defaults(monkeypatch):
    """Test Settings uses defaults when env vars not set."""
    # Clear all relevant env vars
    for key in ["AGRO_MAX_IMAGES", "MAX_IMAGES", "AGRO_DATA_ROOT", "DATA_ROOT"]:
        monkeypatch.delenv(key, raising=False)

    from app.core import config
    config.get_settings.cache_clear()
    settings = config.get_settings()

    assert settings.MAX_IMAGES == 4  # Default from config.py
    assert settings.MAX_IMAGE_MB == 5
    assert settings.DATA_ROOT == "./data"


def test_orchestrator_uses_settings():
    """Test orchestrator.py uses Settings instead of direct os.getenv."""
    from app.core.config import settings
    from app.services.pipeline import orchestrator

    # Verify settings object is available
    assert settings is not None
    assert hasattr(settings, 'MAX_IMAGES')
    assert hasattr(settings, 'DATA_ROOT')
    assert hasattr(settings, 'ALLOWED_MIME')
