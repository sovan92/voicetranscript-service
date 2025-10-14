def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_transcribe_invalid_format(client):
    response = client.post("/transcribe", files={"file": ("test.txt", b"not audio", "text/plain")})
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]

def test_transcribe_success(client, mock_model, dummy_wav_bytes):
    # Reset the mock's call count to ensure a clean state for this test.
    mock_model.transcribe.reset_mock()

    # Create a dummy audio file in memory to send
    files = {"file": ("test.wav", dummy_wav_bytes, "audio/wav")}

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


def test_debug_client_info(client):
    """
    Test the debug endpoint that shows client information.
    """
    response = client.get("/debug/client-info")
    assert response.status_code == 200

    data = response.json()
    assert "client_ip" in data
    assert "headers" in data
    assert isinstance(data["headers"], dict)
