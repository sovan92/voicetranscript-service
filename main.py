from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from contextlib import asynccontextmanager
import tempfile
import os
import logging

# Configure logging to be more informative
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# Custom key function to get the client's real IP address, ignoring the port
def get_client_ip(request: Request) -> str:
    # Check for X-Forwarded-For header (common in proxy/load balancer setups)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in the chain (original client IP)
        client_ip = forwarded_for.split(",")[0].strip()
        logger.info(f"Using X-Forwarded-For IP: {client_ip}")
        return client_ip

    # Check for X-Real-IP header (used by some proxies)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        logger.info(f"Using X-Real-IP: {real_ip}")
        return real_ip

    # Fall back to direct client IP
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Using direct client IP: {client_ip}")
    return client_ip


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=== Application Configuration ===")
    logger.info("Rate limiting: DISABLED")
    logger.info("=== Application Ready ===")
    yield
    # Shutdown (if needed)

app = FastAPI(lifespan=lifespan)

logger.info("Loading transcription model...")
# Load the model once when the application starts
# This is more efficient than loading it for each request.
model_name = os.getenv("WHISPER_MODEL", "tiny")
model = WhisperModel(model_name, device="cpu", compute_type="int8")
logger.info(f"Transcription model '{model_name}' loaded successfully.")


SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "ogg", "flac"]

@app.get("/health")
def health():
    """
    Health check endpoint to verify that the service is running.
    Returns a 200 OK response with a status message.
    """
    logger.info("Health check endpoint was called.")
    return {"status": "ok"}

@app.post("/transcribe")
async def transcribe(request: Request, file: UploadFile = File(...)):
    """
    Transcribes an audio file.

    This endpoint accepts an audio file, validates its format and size,
    and uses the Whisper model to generate a transcription.

    File size limit: 10MB.

    Args:
        request: The incoming request object.
        file: The uploaded audio file.

    Returns:
        A JSON response containing the transcription text.

    Raises:
        HTTPException: If the file format is unsupported, the file size
                       exceeds the limit, or transcription fails.
    """
    client_ip = get_client_ip(request)
    logger.info(f"Processing transcription request for file: {file.filename} from IP: {client_ip}")

    # Read file content into memory to check size
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
        logger.error(f"File size exceeds 10MB for file: {file.filename} from IP: {client_ip}")
        raise HTTPException(
            status_code=413, detail="File size exceeds the limit of 10MB."
        )

    ext = file.filename.split(".")[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported audio format '{ext}' for file: {file.filename} from IP: {client_ip}")
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")

    tmp_path = None
    try:
        # Create a temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        logger.info(f"Saved uploaded file to temporary path: {tmp_path}")

        # Transcribe the audio file
        logger.info(f"Starting transcription for {tmp_path}...")
        segments, info = model.transcribe(tmp_path, beam_size=5)

        # Join the transcribed segments into a single string
        transcript = "".join(segment.text for segment in segments)
        logger.info(f"Transcription successful for file: {file.filename} from IP: {client_ip}")

        return JSONResponse({"transcript": transcript})
    except Exception as e:
        logger.error(f"An error occurred during transcription for IP {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Transcription failed")
    finally:
        # Clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
            logger.info(f"Cleaned up temporary file: {tmp_path}")

# Debug endpoint to check client information
@app.get("/debug/client-info")
async def client_info(request: Request):
    """Debug endpoint to check client information"""
    client_ip = get_client_ip(request)
    return {
        "client_ip": client_ip,
        "headers": dict(request.headers)
    }
