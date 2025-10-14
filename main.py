from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from contextlib import asynccontextmanager
import tempfile
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request headers."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info("Application ready")
    yield


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Load Whisper model at startup
logger.info("Loading transcription model...")
model_name = os.getenv("WHISPER_MODEL", "tiny")
model = WhisperModel(model_name, device="cpu", compute_type="int8")
logger.info(f"Transcription model '{model_name}' loaded successfully")

# Supported audio formats
SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "ogg", "flac"]
FILE_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(request: Request, file: UploadFile = File(...)):
    """
    Transcribe an audio file.

    Args:
        request: The incoming request object
        file: The uploaded audio file

    Returns:
        JSON response containing the transcription text

    Raises:
        HTTPException: If file format is unsupported, file too large, or transcription fails
    """
    client_ip = get_client_ip(request)
    logger.info(f"Transcription request from {client_ip}: {file.filename}")

    # Validate file size
    contents = await file.read()
    if len(contents) > FILE_SIZE_LIMIT:
        logger.error(f"File too large: {len(contents)} bytes from {client_ip}")
        raise HTTPException(
            status_code=413,
            detail="File size exceeds the limit of 10MB."
        )

    # Validate file format
    ext = file.filename.split(".")[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported format '{ext}' from {client_ip}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {ext}"
        )

    tmp_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Transcribe audio
        logger.info(f"Starting transcription: {tmp_path}")
        segments, info = model.transcribe(tmp_path, beam_size=5)
        transcript = "".join(segment.text for segment in segments)

        logger.info(f"Transcription completed for {client_ip}")
        return JSONResponse({"transcript": transcript})

    except Exception as e:
        logger.error(f"Transcription failed for {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Transcription failed")
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/debug/client-info")
async def client_info(request: Request):
    """Debug endpoint to check client information."""
    return {
        "client_ip": get_client_ip(request),
        "headers": dict(request.headers)
    }
