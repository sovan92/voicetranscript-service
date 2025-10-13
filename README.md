# Voice Transcript Service

## Architecture Overview
A FastAPI service exposes endpoints to transcribe audio files using open-source Whisper. It provides health and transcription endpoints, error handling, logging, and can be containerized/deployed via Docker. CI/CD is set up with GitHub Actions.

## Features
- **Rate Limiting**: To prevent abuse, the `/transcribe` endpoint is rate-limited to 5 requests per minute per IP address.
- **File Size Limit**: The maximum allowed file size for transcription is 10MB. Requests with larger files will be rejected.

## Local Development
1. Clone repo
2. Create virtual environment: `python3 -m venv venv`
3. Activate virtual environment: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start service: `uvicorn main:app --host 0.0.0.0 --port 8000`

## How to Run Tests
`python -m pytest`

## Deployment
Deployment is automated via a CI/CD pipeline using GitHub Actions. A push to the `main` branch will trigger the following workflow:
1.  Tests are run.
2.  A new Docker image is built and pushed to GitHub Container Registry (GHCR).
3.  The new image is deployed to the configured EC2 instance, where the service is restarted using `docker-compose`.

For this to work, the following secrets must be configured in the repository's `Settings` > `Secrets and variables` > `Actions`:
- `EC2_HOST`: The IP address or domain of the EC2 instance.
- `EC2_USERNAME`: The SSH username for the EC2 instance (e.g., `ubuntu`).
- `EC2_PRIVATE_KEY`: The private SSH key for the EC2 instance.

## Example Usage

### Using Local Instance
- Health check: `curl http://localhost:8000/health`
- Transcription: `curl -F "file=@harvard.wav" http://localhost:8000/transcribe`
- Minimal client: `python minimal-client.py http://localhost:8000 harvard.wav`

### Using Deployed Instance
- Health check: `curl http://<EC2_HOST>:8000/health`
- Transcription: `curl -F "file=@harvard.wav" http://<EC2_HOST>:8000/transcribe`
- Using Python client: `python minimal-client.py http://<EC2_HOST>:8000 harvard.wav`

## Supported Formats
wav, mp3, m4a, ogg, flac

## Dependencies
The service requires the following Python packages, which are listed in `requirements.txt`:
```
fastapi
uvicorn
openai-whisper
python-multipart
pydantic
pytest
httpx
```

## Notes
- Error handling/logging included
- Secrets via env vars (if needed)
- Trade-offs: Whisper is accurate but resource-intensive; for scale, consider faster-whisper or Vosk
- Next steps: add streaming, auth, frontend client
