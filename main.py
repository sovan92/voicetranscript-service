from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from faster_whisper import WhisperModel
import tempfile
import os
import logging
import redis

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
        logger.info(f"Rate limiter using X-Forwarded-For IP: {client_ip}")
        return client_ip

    # Check for X-Real-IP header (used by some proxies)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        logger.info(f"Rate limiter using X-Real-IP: {real_ip}")
        return real_ip

    # Fall back to direct client IP
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Rate limiter using direct client IP: {client_ip}")
    return client_ip


# Connect to Redis for centralized rate limit storage with better error handling
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
logger.info(f"Connecting to Redis at: {redis_url}")

try:
    # Test Redis connection with a timeout
    redis_client = redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
    redis_client.ping()
    logger.info("Redis connection successful - using Redis for rate limiting")
    limiter = Limiter(key_func=get_client_ip, storage_uri=redis_url)
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Falling back to in-memory rate limiting.")
    # Fall back to in-memory storage if Redis is not available
    limiter = Limiter(key_func=get_client_ip)

app = FastAPI()
app.state.limiter = limiter

@app.on_event("startup")
async def startup_event():
    """Log rate limiter configuration on startup"""
    logger.info("=== Rate Limiter Configuration ===")
    logger.info(f"Limiter type: {type(limiter)}")
    logger.info(f"Redis URL: {redis_url}")

    # Test Redis connection if using Redis storage
    if redis_url and not redis_url.startswith("memory://"):
        try:
            redis_client.ping()
            logger.info("✅ Redis connection verified - Rate limiting will work across container restarts")
        except Exception as e:
            logger.error(f"❌ Redis connection issue: {e}")
    else:
        logger.warning("⚠️ Using in-memory storage - Rate limits will reset on container restart")

    logger.info("=== Rate Limiter Ready ===")

# Add a custom rate limit exceeded handler with better logging
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    client_ip = get_client_ip(request)
    logger.warning(f"Rate limit exceeded for IP: {client_ip} - {exc.detail}")
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )

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
    File size limit: 10MB.

    Args:
        request: The incoming request object (used for rate limiting).
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

# Debug endpoint to check rate limiter status
@app.get("/debug/rate-limit-info")
async def rate_limit_info(request: Request):
    """Debug endpoint to check rate limit configuration"""
    client_ip = get_client_ip(request)
    return {
        "client_ip": client_ip,
        "limiter_type": str(type(limiter)),
        "rate_limit_key": limiter.key_func(request),
        "headers": dict(request.headers)
    }
