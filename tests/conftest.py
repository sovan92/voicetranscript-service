import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import io
import wave

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture(scope="module")
def dummy_wav_bytes():
    """
    Creates in-memory bytes for a silent WAV file.
    """
    wav_output = io.BytesIO()
    with wave.open(wav_output, "wb") as wf:
        wf.setnchannels(1)  # mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(16000)  # 16kHz
        wf.writeframes(b"\x00\x00" * 1600)  # 0.1 seconds of silence
    wav_output.seek(0)
    return wav_output.read()

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
    This fixture sets up the test client. It patches the WhisperModel
    to prevent the real model from being loaded during testing.
    """
    # Patch the model before importing the app to prevent it from loading
    with patch("faster_whisper.WhisperModel", return_value=mock_model):
        from main import app
        with TestClient(app) as test_client:
            yield test_client
