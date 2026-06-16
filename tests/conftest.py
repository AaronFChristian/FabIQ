"""
Shared pytest fixtures for FabIQ tests.

Uses environment variable overrides to avoid requiring real Azure credentials
in CI. Azure calls are mocked via pytest-mock where needed.
"""
import os
import pytest

# Override all secrets before any module imports settings
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("AZURE_SEARCH_ENDPOINT", "https://test.search.windows.net")
os.environ.setdefault("AZURE_SEARCH_API_KEY", "test-search-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")


@pytest.fixture
def sample_text() -> str:
    return """
EUV Lithography System Maintenance Guide

1. Overview
The ASML EUV lithography system operates at 13.5nm wavelength using a
laser-produced plasma (LPP) light source. The system requires weekly
calibration of the projection optics module.

2. Calibration Procedure
2.1 Power down the light source
2.2 Run the automated alignment sequence (takes approximately 45 minutes)
2.3 Verify wavefront error is below 0.5nm RMS
2.4 Log results in the maintenance tracking system

3. Common Issues
- Focus drift: recalibrate the auto-focus sensor array
- Overlay error: check reticle stage position encoders
- Dose uniformity: inspect the illumination system apertures
"""


@pytest.fixture
def sample_pdf_text() -> str:
    return "Semiconductor process specification document\n\n" + "Content paragraph. " * 200
