"""
Comprehensive tests for the voice transcription service.

This module contains tests for all endpoints, error handling, validation,
and various edge cases to ensure the service works correctly.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from typing import Dict


class TestHealthEndpoint:
    """Test cases for the health check endpoint."""

    def test_health_check_success(self, client: TestClient):
        """Test successful health check with model loaded."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "model" in data
        assert "limits" in data

        # Verify health status
        assert data["status"] == "healthy"
        assert data["service"] == "voice-transcription-service"
        assert data["version"] == "1.0.0"

        # Verify model information
        model_info = data["model"]
        assert model_info["name"] == "tiny"
        assert model_info["device"] == "cpu"
        assert model_info["status"] == "loaded"

        # Verify limits
        limits = data["limits"]
        assert limits["max_file_size_mb"] == 10
        assert limits["max_duration_seconds"] == 300
        assert isinstance(limits["supported_formats"], list)
        assert "wav" in limits["supported_formats"]

    def test_health_check_with_model_failure(self):
        """Test health check when model loading fails."""
        with patch("main.model", None):
            with patch("main.WhisperModel", return_value=None):
                from main import app
                with TestClient(app) as client:
                    response = client.get("/health")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "unhealthy"
                    assert data["model"]["status"] == "not_loaded"


class TestTranscriptionEndpoint:
    """Test cases for the transcription endpoint."""

    def test_transcribe_success(self, client: TestClient, test_audio_files: Dict[str, bytes]):
        """Test successful audio transcription."""
        files = {"file": ("test.wav", test_audio_files["wav"], "audio/wav")}

        response = client.post("/transcribe", files=files)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "transcript" in data
        assert "metadata" in data

        # Verify transcript content
        assert data["transcript"] == "This is a test transcript."

        # Verify metadata
        metadata = data["metadata"]
        assert metadata["filename"] == "test.wav"
        assert metadata["model_used"] == "tiny"
        assert "request_id" in metadata
        assert "file_size_bytes" in metadata

    def test_transcribe_empty_result(self, client_empty_transcription: TestClient, test_audio_files: Dict[str, bytes]):
        """Test transcription when no speech is detected."""
        files = {"file": ("silent.wav", test_audio_files["wav"], "audio/wav")}

        response = client_empty_transcription.post("/transcribe", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["transcript"] == "[No speech detected]"

    def test_transcribe_model_error(self, client_transcription_error: TestClient, test_audio_files: Dict[str, bytes]):
        """Test transcription when model throws an error."""
        files = {"file": ("error.wav", test_audio_files["wav"], "audio/wav")}

        response = client_transcription_error.post("/transcribe", files=files)

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Transcription Error"
        assert "Transcription failed" in data["message"]
        assert data["error_code"] == "TRANSCRIPTION_FAILED"

    def test_transcribe_different_formats(self, client: TestClient, test_audio_files: Dict[str, bytes]):
        """Test transcription with different audio formats."""
        test_cases = [
            ("test.wav", "audio/wav"),
            ("test.mp3", "audio/mp3"),
            ("test.m4a", "audio/mp4"),
            ("test.ogg", "audio/ogg"),
            ("test.flac", "audio/flac")
        ]

        for filename, content_type in test_cases:
            files = {"file": (filename, test_audio_files["wav"], content_type)}
            response = client.post("/transcribe", files=files)
            assert response.status_code == 200, f"Failed for format: {filename}"

    def test_transcribe_unsupported_format(self, client: TestClient, test_audio_files: Dict[str, bytes]):
        """Test transcription with unsupported file format."""
        files = {"file": ("test.txt", test_audio_files["tiny"], "text/plain")}

        response = client.post("/transcribe", files=files)

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Validation Error"
        assert "Unsupported audio format: txt" in data["message"]
        assert data["error_code"] == "UNSUPPORTED_FORMAT"

    def test_transcribe_file_too_large(self, client: TestClient, test_audio_files: Dict[str, bytes]):
        """Test transcription with file exceeding size limit."""
        files = {"file": ("large.wav", test_audio_files["large"], "audio/wav")}

        response = client.post("/transcribe", files=files)

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Validation Error"
        assert "exceeds limit of 10MB" in data["message"]
        assert data["error_code"] == "FILE_TOO_LARGE"

    def test_transcribe_empty_file(self, client: TestClient):
        """Test transcription with empty file."""
        files = {"file": ("empty.wav", b"", "audio/wav")}

        response = client.post("/transcribe", files=files)

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Validation Error"
        assert data["message"] == "Empty file uploaded"
        assert data["error_code"] == "EMPTY_FILE"

    def test_transcribe_no_filename(self, client: TestClient, test_audio_files: Dict[str, bytes]):
        """Test transcription with missing filename."""
        # Create file upload without filename
        response = client.post(
            "/transcribe",
            files={"file": (None, test_audio_files["wav"], "audio/wav")}
        )

        # FastAPI handles this at the request parsing level, returning 422
        assert response.status_code == 422

    def test_transcribe_missing_file(self, client: TestClient):
        """Test transcription endpoint without file parameter."""
        response = client.post("/transcribe")

        assert response.status_code == 422  # FastAPI validation error

    def test_transcribe_invalid_multipart(self, client: TestClient):
        """Test transcription with invalid multipart data."""
        response = client.post(
            "/transcribe",
            data={"not_a_file": "invalid"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 422


class TestValidation:
    """Test cases for input validation functionality."""

    def test_get_client_ip_forwarded_for(self, client: TestClient):
        """Test client IP detection with X-Forwarded-For header."""
        response = client.get(
            "/debug/client-info",
            headers={"X-Forwarded-For": "203.0.113.1, 198.51.100.1"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["client_ip"] == "203.0.113.1"

    def test_get_client_ip_real_ip(self, client: TestClient):
        """Test client IP detection with X-Real-IP header."""
        response = client.get(
            "/debug/client-info",
            headers={"X-Real-IP": "203.0.113.2"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["client_ip"] == "203.0.113.2"

    def test_get_client_ip_fallback(self, client: TestClient):
        """Test client IP detection fallback to direct connection."""
        response = client.get("/debug/client-info")

        assert response.status_code == 200
        data = response.json()
        # TestClient uses "testclient" as the default client host
        assert data["client_ip"] == "testclient"


class TestDebugEndpoint:
    """Test cases for debug endpoints."""

    def test_debug_client_info(self, client: TestClient):
        """Test debug endpoint for client information."""
        response = client.get(
            "/debug/client-info",
            headers={"User-Agent": "test-client/1.0"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "client_ip" in data
        assert "headers" in data
        assert "method" in data
        assert "url" in data
        assert "user_agent" in data

        # Verify content
        assert data["method"] == "GET"
        assert data["user_agent"] == "test-client/1.0"
        assert "/debug/client-info" in data["url"]


class TestErrorHandling:
    """Test cases for error handling and edge cases."""

    def test_404_endpoint(self, client: TestClient):
        """Test accessing non-existent endpoint."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client: TestClient):
        """Test using wrong HTTP method."""
        response = client.get("/transcribe")
        assert response.status_code == 405

    def test_health_endpoint_resilience(self, client: TestClient):
        """Test health endpoint resilience to various conditions."""
        # Test multiple rapid requests
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200

    def test_concurrent_transcription_requests(self, client: TestClient, test_audio_files: Dict[str, bytes]):
        """Test handling multiple concurrent transcription requests."""
        files = {"file": ("test.wav", test_audio_files["wav"], "audio/wav")}

        # Simulate concurrent requests (TestClient is synchronous, but tests the code path)
        responses = []
        for i in range(3):
            response = client.post("/transcribe", files=files)
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "transcript" in data


class TestIntegration:
    """Integration tests covering full request/response cycles."""

    def test_full_transcription_workflow(self, client: TestClient, test_audio_files: Dict[str, bytes]):
        """Test complete transcription workflow from upload to response."""
        # 1. Check health
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

        # 2. Get debug info
        debug_response = client.get("/debug/client-info")
        assert debug_response.status_code == 200

        # 3. Transcribe audio
        files = {"file": ("integration_test.wav", test_audio_files["wav"], "audio/wav")}
        transcribe_response = client.post("/transcribe", files=files)

        assert transcribe_response.status_code == 200
        data = transcribe_response.json()

        # Verify complete response structure
        assert isinstance(data["transcript"], str)
        assert len(data["transcript"]) > 0
        assert data["metadata"]["filename"] == "integration_test.wav"
        assert data["metadata"]["model_used"] == "tiny"

    def test_api_documentation_accessible(self, client: TestClient):
        """Test that API documentation endpoints are accessible."""
        # Test OpenAPI docs
        docs_response = client.get("/docs")
        assert docs_response.status_code == 200

        # Test ReDoc
        redoc_response = client.get("/redoc")
        assert redoc_response.status_code == 200

        # Test OpenAPI schema
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200

        # Verify it's valid JSON
        schema = openapi_response.json()
        assert "openapi" in schema
        assert "paths" in schema
