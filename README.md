# Voice Transcript Service

## Architecture Overview
A FastAPI service exposes endpoints to transcribe audio files using open-source Whisper. It provides health and transcription endpoints, error handling, logging, and can be containerized/deployed via Docker. CI/CD is set up with GitHub Actions.

## Local Development
1. Clone repo
2. Install dependencies: `pip install -r requirements.txt`
3. Start service: `uvicorn main:app --reload`

## How to Run Tests
`pytest`

## How to Start Service Locally
`uvicorn main:app --host 0.0.0.0 --port 8000`

## Deployment Steps
- Build Docker image: `docker build -t voicetranscript-service .`
- Run with Docker Compose: `docker-compose up`
- For Ubuntu server: copy files, run above commands

## Example Usage
- Health check: `curl http://localhost:8000/health`
- Transcription: `curl -F "file=@sample.wav" http://localhost:8000/transcribe`
- Minimal client: `python client.py`

## Supported Formats
wav, mp3, m4a, ogg, flac

## Notes
- Error handling/logging included
- Secrets via env vars (if needed)
- Trade-offs: Whisper is accurate but resource-intensive; for scale, consider faster-whisper or Vosk
- Next steps: add streaming, auth, frontend client
fastapi
uvicorn
openai-whisper
python-multipart
pydantic
pytest
httpx

