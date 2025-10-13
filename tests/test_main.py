def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_transcribe_invalid_format(client):
    response = client.post("/transcribe", files={"file": ("test.txt", b"not audio", "text/plain")})
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]

def test_transcribe_success(client, mock_model):
    # Reset the mock's call count to ensure a clean state for this test.
    mock_model.transcribe.reset_mock()

    # Create a dummy audio file in memory to send
    dummy_audio_content = b"dummy wav content"
    files = {"file": ("test.wav", dummy_audio_content, "audio/wav")}

    # Call the endpoint
    response = client.post("/transcribe", files=files)

    # Check the response
    assert response.status_code == 200
    assert response.json() == {"transcript": "This is a test transcript."}

    # Verify that the mock transcribe method was called
    mock_model.transcribe.assert_called_once()


def test_transcribe_file_too_large(client):
    """
    Test that uploading a file larger than 10MB returns a 413 error.
    """
    # Create a dummy file that is just over the 10MB limit
    large_content = b"a" * (10 * 1024 * 1024 + 1)
    files = {"file": ("large_file.wav", large_content, "audio/wav")}

    response = client.post("/transcribe", files=files)

    assert response.status_code == 413
    assert response.json()["detail"] == "File size exceeds the limit of 10MB."


def test_transcribe_rate_limit(client, mock_model):
    """
    Test that the rate limit of 5 requests per minute is enforced.
    """
    # Use a small, valid file for the requests
    dummy_audio_content = b"dummy wav content"
    files = {"file": ("test.wav", dummy_audio_content, "audio/wav")}

    # Make 5 requests, which should succeed
    for i in range(5):
        response = client.post("/transcribe", files=files)
        assert response.status_code == 200, f"Request {i+1} failed unexpectedly"

    # The 6th request should be rate-limited
    response = client.post("/transcribe", files=files)
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]
