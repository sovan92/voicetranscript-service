import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def mock_model():
    """
    This fixture creates a mock of the WhisperModel instance.
    It's scoped to the module to be efficient.
    """
    mock_model_instance = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "This is a test transcript."
    mock_model_instance.transcribe.return_value = ([mock_segment], "info")
    return mock_model_instance

@pytest.fixture(scope="module")
def client(mock_model):
    """
    This fixture sets up the test client. It patches the 'model' object
    in the 'main' module BEFORE the app is imported for testing.
    This is the key to ensuring the real model is never loaded.
    """
    with patch("main.model", mock_model):
        from main import app
        with TestClient(app) as test_client:
            yield test_client

