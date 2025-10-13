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
