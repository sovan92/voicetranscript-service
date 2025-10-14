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

## 🚀 CI/CD Deployment to EC2

This project is configured with a Continuous Integration and Continuous Deployment (CI/CD) pipeline using GitHub Actions to automatically deploy the service to an AWS EC2 instance.

The workflow is defined in `.github/workflows/ci.yml` and consists of two main jobs: `build-test` and `deploy`.

### Build and Test (`build-test`)

This job runs on every push to the `main` branch.

1.  **Checkout & Setup**: Checks out the code and sets up the Python environment.
2.  **Lint & Test**: Runs a series of quality checks, including linting with `flake8`, type checking with `mypy`, and running unit tests with `pytest`.
3.  **Build & Push Docker Image**: If all checks pass, it builds a Docker image of the application. The image is tagged with the short Git SHA and `latest`. Both tags are then pushed to GitHub Container Registry (GHCR).

### Deploy (`deploy`)

This job runs only after the `build-test` job succeeds on the `main` branch.

1.  **Update Compose File**: It updates the `docker/docker-compose.prod.yml` file to use the newly built Docker image tag.
2.  **Stop Existing Containers**: It connects to the EC2 instance via SSH and runs `docker-compose down` to gracefully stop and remove the currently running application containers.
3.  **Copy Compose File**: The updated `docker-compose.prod.yml` is securely copied to the EC2 instance.
4.  **Deploy New Version**: It connects to the EC2 instance again to perform the final deployment steps:
    *   Logs in to GHCR to access the private image.
    *   Pulls the new Docker image.
    *   Prunes old, unused Docker images to save space.
    *   Starts the new application container in detached mode using `docker-compose up -d`.

This automated process ensures that every change pushed to the `main` branch is automatically tested and deployed, providing a seamless and reliable delivery pipeline.

### Required Secrets

To enable the deployment to EC2, the following secrets must be configured in your GitHub repository's **Settings > Secrets and variables > Actions**:

-   `EC2_HOST`: The public IP address or DNS name of your EC2 instance.
-   `EC2_USERNAME`: The username for connecting to your EC2 instance (e.g., `ubuntu` or `ec2-user`).
-   `EC2_PRIVATE_KEY`: The private SSH key that corresponds to a public key in the `~/.ssh/authorized_keys` file on your EC2 instance. This allows the workflow to securely connect to your instance.
    > **Note:** The private key will be provided upon request. Please share a secure link to receive it.

The `GITHUB_TOKEN` is also used for authentication against the GitHub Container Registry, but it is automatically provided by GitHub Actions and does not need to be configured manually.

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
