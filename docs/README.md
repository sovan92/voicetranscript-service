# Voice Transcription Service

A FastAPI-based microservice for transcribing audio files using OpenAI's Whisper model.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python -m uvicorn src.voicetranscript.main:app --reload

# Or using the run script
./scripts/dev-check.sh
```

## 📁 Project Structure

```
voicetranscript-service/
├── src/
│   └── voicetranscript/          # Main application package
│       ├── __init__.py
│       └── main.py               # FastAPI application
├── tests/                        # Test suite
│   ├── conftest.py
│   └── test_main.py
├── docs/                         # Documentation
│   ├── README.md
│   └── Zoom-Info-Question.md
├── scripts/                      # Utility scripts
│   ├── dev-check.sh
│   └── minimal-client.py
├── docker/                       # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.prod.yml
├── resources/                    # Static resources
│   ├── audio/                    # Sample audio files
│   └── config/                   # Configuration files
├── logs/                         # Application logs
├── requirements.txt              # Python dependencies
└── pyproject.toml               # Project configuration
```

## 🛠 Development

### Running Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run tests with coverage
python -m pytest tests/ -v --cov=src/voicetranscript
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## 🐳 Docker

```bash
# Build and run with Docker Compose
cd docker/
docker-compose -f docker-compose.prod.yml up --build
```

## 📚 API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🎵 Supported Audio Formats

- WAV
- MP3
- M4A
- OGG
- FLAC
- WebM
- MP4
