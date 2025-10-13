import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

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

@pytest.fixture(scope="function")
def client(mock_model):
    """
    This fixture sets up the test client. It patches the 'model' object
    in the 'main' module BEFORE the app is imported for testing.
    This is the key to ensuring the real model is never loaded.
    """
    # Reset the limiter's storage before each test that uses this client
    from main import limiter
    limiter.reset()

    with patch("main.model", mock_model):
        from main import app
        with TestClient(app) as test_client:
            yield test_client
