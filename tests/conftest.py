"""
Test configuration and fixtures for the voice transcription service.

This module provides test fixtures and configuration for testing the FastAPI
application with proper mocking and test data generation.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import io
import wave
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any

# Add the project root and src directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)


@pytest.fixture(scope="session")
def test_audio_files() -> Dict[str, bytes]:
    """
    Create various test audio files for comprehensive testing.

    Returns:
        Dict mapping file types to their byte content
    """
    audio_files = {}

    # Create a short WAV file (0.1 seconds of silence)
    wav_output = io.BytesIO()
    with wave.open(wav_output, "wb") as wf:
        wf.setnchannels(1)  # mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(16000)  # 16kHz
        wf.writeframes(b"\x00\x00" * 1600)  # 0.1 seconds of silence
    wav_output.seek(0)
    audio_files["wav"] = wav_output.read()

    # Create a very small file for testing
    audio_files["tiny"] = b"small_audio_data"

    # Create a large file for size limit testing (just over 10MB)
    audio_files["large"] = b"a" * (10 * 1024 * 1024 + 1)

    return audio_files


@pytest.fixture(scope="session")
def mock_whisper_model() -> MagicMock:
    """
    Create a mock WhisperModel instance with realistic behavior.

    Returns:
        Mock WhisperModel instance
    """
    mock_model = MagicMock()

    # Create mock segment
    mock_segment = MagicMock()
    mock_segment.text = " This is a test transcript."
    mock_segment.start = 0.0
    mock_segment.end = 2.5

    # Create mock info
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.95

    # Configure the transcribe method
    mock_model.transcribe.return_value = ([mock_segment], mock_info)

    return mock_model


@pytest.fixture(scope="session")
def mock_whisper_model_empty() -> MagicMock:
    """
    Create a mock WhisperModel that returns empty transcription.

    Returns:
        Mock WhisperModel instance that returns no segments
    """
    mock_model = MagicMock()

    # Create mock info
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.50

    # Configure to return empty segments
    mock_model.transcribe.return_value = ([], mock_info)

    return mock_model


@pytest.fixture(scope="session")
def mock_whisper_model_error() -> MagicMock:
    """
    Create a mock WhisperModel that raises an exception.

    Returns:
        Mock WhisperModel instance that raises exceptions
    """
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = Exception("Transcription failed")
    return mock_model


@pytest.fixture(scope="function")
def client(mock_whisper_model: MagicMock) -> Generator[TestClient, None, None]:
    """
    Create a test client with mocked WhisperModel.

    Args:
        mock_whisper_model: Mocked Whisper model

    Yields:
        TestClient instance for testing
    """
    # Patch the WhisperModel before importing the app
    with patch("voicetranscript.main.WhisperModel", return_value=mock_whisper_model):
        # Import after patching to ensure the mock is used
        from voicetranscript.main import app

        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture(scope="function")
def client_empty_transcription(mock_whisper_model_empty: MagicMock) -> Generator[TestClient, None, None]:
    """
    Create a test client that returns empty transcriptions.

    Args:
        mock_whisper_model_empty: Mock model that returns empty results

    Yields:
        TestClient instance for testing empty transcription scenarios
    """
    with patch("voicetranscript.main.WhisperModel", return_value=mock_whisper_model_empty):
        from voicetranscript.main import app

        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture(scope="function")
def client_transcription_error(mock_whisper_model_error: MagicMock) -> Generator[TestClient, None, None]:
    """
    Create a test client that simulates transcription errors.

    Args:
        mock_whisper_model_error: Mock model that raises exceptions

    Yields:
        TestClient instance for testing error scenarios
    """
    with patch("voicetranscript.main.WhisperModel", return_value=mock_whisper_model_error):
        from voicetranscript.main import app

        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def temp_audio_file() -> Generator[str, None, None]:
    """
    Create a temporary audio file for testing.

    Yields:
        Path to temporary audio file
    """
    # Create temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        with wave.open(tmp_file.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 8000)  # 0.5 seconds

        yield tmp_file.name

    # Clean up
    try:
        os.unlink(tmp_file.name)
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Set up test environment variables and cleanup.
    """
    # Set test environment variables
    os.environ["WHISPER_MODEL"] = "tiny"
    os.environ["WHISPER_DEVICE"] = "cpu"
    os.environ["WHISPER_COMPUTE_TYPE"] = "int8"

    yield

    # Cleanup any test files that might have been created
    test_files = ["app.log", "test.log"]
    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
