from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from faster_whisper import WhisperModel
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


# Create a rate limiter instance
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
@limiter.limit("5/minute")
async def transcribe(request: Request, file: UploadFile = File(...)):
    """
    Transcribes an audio file.

    This endpoint accepts an audio file, validates its format and size,
    and uses the Whisper model to generate a transcription.

    Rate limiting: 5 requests per minute per IP address.
    File size limit: 100KB.

    Args:
        request: The incoming request object (used for rate limiting).
        file: The uploaded audio file.

    Returns:
        A JSON response containing the transcription text.

    Raises:
        HTTPException: If the file format is unsupported, the file size
                       exceeds the limit, or transcription fails.
    """
    logger.info(f"Received transcription request for file: {file.filename}")

    # Read file content into memory to check size
    contents = await file.read()
    if len(contents) > 100 * 1024:  # 100 KB limit
        logger.error(f"File size exceeds 100KB for file: {file.filename}")
        raise HTTPException(
            status_code=413, detail="File size exceeds the limit of 100KB."
        )

    ext = file.filename.split(".")[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported audio format '{ext}' for file: {file.filename}")
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
        logger.info(f"Transcription successful for file: {file.filename}")

        return JSONResponse({"transcript": transcript})
    except Exception as e:
        logger.error(f"An error occurred during transcription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Transcription failed")
    finally:
        # Clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
            logger.info(f"Cleaned up temporary file: {tmp_path}")
