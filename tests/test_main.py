import sys
import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path to resolve the ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_transcribe_invalid_format():
    response = client.post("/transcribe", files={"file": ("test.txt", b"not audio", "text/plain")})
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]

def test_transcribe_success():
    # Mock the model's transcribe method to avoid running a real transcription
    with patch('main.model.transcribe') as mock_transcribe:
        # Configure the mock to return a value similar to the real method
        mock_segment = MagicMock()
        mock_segment.text = "This is a test transcript."
        mock_transcribe.return_value = ([mock_segment], "info")

        # Create a dummy audio file in memory to send
        dummy_audio_content = b"dummy wav content"
        files = {"file": ("test.wav", dummy_audio_content, "audio/wav")}

        # Call the endpoint
        response = client.post("/transcribe", files=files)

        # Check the response
        assert response.status_code == 200
        assert response.json() == {"transcript": "This is a test transcript."}

        # Verify that the transcribe method was called
        mock_transcribe.assert_called_once()
