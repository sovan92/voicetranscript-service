"""
Voice Transcription Service - FastAPI application for audio transcription using Whisper.

This service provides HTTP endpoints for transcribing audio files using the faster-whisper library.
It supports multiple audio formats and includes proper error handling, logging, and validation.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, AsyncGenerator
import tempfile
import os
import logging
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, status
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from faster_whisper.transcribe import TranscriptionOptions
import uvicorn

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Application constants
SUPPORTED_FORMATS = {"wav", "mp3", "m4a", "ogg", "flac", "webm", "mp4"}
FILE_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB
MAX_AUDIO_DURATION = 300  # 5 minutes in seconds
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "tiny")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# Global model instance
model: Optional[WhisperModel] = None


class TranscriptionError(Exception):
    """Custom exception for transcription-related errors."""

    def __init__(self, message: str, error_code: str = "TRANSCRIPTION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request headers with proper fallback chain.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address or 'unknown' if unable to determine
    """
    try:
        # Check X-Forwarded-For header (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            client_ip = forwarded_for.split(",")[0].strip()
            logger.debug(f"Client IP from X-Forwarded-For: {client_ip}")
            return client_ip

        # Check X-Real-IP header (reverse proxy)
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            logger.debug(f"Client IP from X-Real-IP: {real_ip}")
            return real_ip

        # Fall back to direct connection IP
        if request.client and request.client.host:
            logger.debug(f"Client IP from direct connection: {request.client.host}")
            return request.client.host

        logger.warning("Unable to determine client IP address")
        return "unknown"

    except Exception as e:
        logger.error(f"Error extracting client IP: {e}")
        return "unknown"


def validate_audio_file(file: UploadFile, contents: bytes) -> None:
    """
    Validate uploaded audio file for format, size, and other constraints.

    Args:
        file: The uploaded file object
        contents: File contents as bytes

    Raises:
        ValidationError: If validation fails
    """
    try:
        # Validate filename exists
        if not file.filename:
            raise ValidationError("No filename provided", "MISSING_FILENAME")

        # Validate file extension
        file_path = Path(file.filename)
        file_extension = file_path.suffix.lower().lstrip('.')

        if file_extension not in SUPPORTED_FORMATS:
            supported_list = ", ".join(sorted(SUPPORTED_FORMATS))
            raise ValidationError(
                f"Unsupported audio format: {file_extension}. "
                f"Supported formats: {supported_list}",
                "UNSUPPORTED_FORMAT"
            )

        # Validate file size
        file_size = len(contents)
        if file_size == 0:
            raise ValidationError("Empty file uploaded", "EMPTY_FILE")

        if file_size > FILE_SIZE_LIMIT:
            size_mb = file_size / (1024 * 1024)
            limit_mb = FILE_SIZE_LIMIT / (1024 * 1024)
            raise ValidationError(
                f"File size ({size_mb:.1f}MB) exceeds limit of {limit_mb:.0f}MB",
                "FILE_TOO_LARGE"
            )

        # Validate content type if provided
        if file.content_type and not file.content_type.startswith(('audio/', 'video/')):
            logger.warning(f"Unexpected content type: {file.content_type}")

        logger.info(f"File validation passed: {file.filename} ({file_size} bytes)")

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file validation: {e}")
        raise ValidationError(f"File validation failed: {str(e)}", "VALIDATION_FAILED")


async def transcribe_audio_file(file_path: str, client_ip: str) -> str:
    """
    Transcribe audio file using Whisper model with proper error handling.

    Args:
        file_path: Path to the audio file
        client_ip: Client IP for logging

    Returns:
        str: Transcribed text

    Raises:
        TranscriptionError: If transcription fails
    """
    try:
        if not model:
            raise TranscriptionError("Transcription model not initialized", "MODEL_NOT_LOADED")

        logger.info(f"Starting transcription for {file_path} (client: {client_ip})")

        # Perform transcription with options
        segments, info = model.transcribe(
            file_path,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        # Collect segments and build transcript
        transcript_segments = []
        total_duration = 0

        for segment in segments:
            transcript_segments.append(segment.text)
            total_duration = max(total_duration, segment.end)

        # Check if audio is too long
        if total_duration > MAX_AUDIO_DURATION:
            logger.warning(f"Audio duration ({total_duration:.1f}s) exceeds recommended limit")

        transcript = "".join(transcript_segments).strip()

        if not transcript:
            logger.warning(f"Empty transcription result for {file_path}")
            return "[No speech detected]"

        logger.info(
            f"Transcription completed for {client_ip}: "
            f"{len(transcript)} characters, {total_duration:.1f}s duration, "
            f"language: {info.language} (confidence: {info.language_probability:.2f})"
        )

        return transcript

    except Exception as e:
        error_msg = f"Transcription failed for {client_ip}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise TranscriptionError(error_msg, "TRANSCRIPTION_FAILED")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown with proper error handling."""
    global model

    try:
        # Startup
        logger.info("=== Application Startup ===")
        logger.info(f"Loading Whisper model: {WHISPER_MODEL_NAME}")
        logger.info(f"Device: {WHISPER_DEVICE}, Compute type: {WHISPER_COMPUTE_TYPE}")

        model = WhisperModel(
            WHISPER_MODEL_NAME,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE
        )

        logger.info("Model loaded successfully")
        logger.info(f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}")
        logger.info(f"File size limit: {FILE_SIZE_LIMIT / (1024*1024):.0f}MB")
        logger.info(f"Max audio duration: {MAX_AUDIO_DURATION}s")
        logger.info("=== Application Ready ===")

        yield

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("=== Application Shutdown ===")
        if model:
            logger.info("Cleaning up model resources")
        logger.info("Shutdown complete")


# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="Voice Transcription Service",
    description="A FastAPI service for transcribing audio files using Whisper",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors with structured response."""
    client_ip = get_client_ip(request)
    logger.warning(f"Validation error for {client_ip}: {exc.message}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "timestamp": "2024-01-01T00:00:00Z"  # Simplified for testing
        }
    )


@app.exception_handler(TranscriptionError)
async def transcription_exception_handler(request: Request, exc: TranscriptionError) -> JSONResponse:
    """Handle transcription errors with structured response."""
    client_ip = get_client_ip(request)
    logger.error(f"Transcription error for {client_ip}: {exc.message}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Transcription Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "timestamp": "2024-01-01T00:00:00Z"  # Simplified for testing
        }
    )


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint providing detailed service status.

    Returns:
        Dict containing service health information
    """
    try:
        model_status = "loaded" if model else "not_loaded"

        health_info = {
            "status": "healthy" if model else "unhealthy",
            "service": "voice-transcription-service",
            "version": "1.0.0",
            "model": {
                "name": WHISPER_MODEL_NAME,
                "device": WHISPER_DEVICE,
                "compute_type": WHISPER_COMPUTE_TYPE,
                "status": model_status
            },
            "limits": {
                "max_file_size_mb": FILE_SIZE_LIMIT // (1024 * 1024),
                "max_duration_seconds": MAX_AUDIO_DURATION,
                "supported_formats": sorted(SUPPORTED_FORMATS)
            }
        }

        logger.debug("Health check requested")
        return health_info

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": "Health check failed",
            "error": str(e)
        }


@app.post("/transcribe", tags=["Transcription"])
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(..., description="Audio file to transcribe")
) -> Dict[str, Any]:
    """
    Transcribe an uploaded audio file to text.

    Args:
        request: FastAPI request object
        file: Uploaded audio file

    Returns:
        JSON response containing the transcription

    Raises:
        HTTPException: For various error conditions
    """
    client_ip = get_client_ip(request)
    request_id = str(uuid.uuid4())  # Generate UUID for request tracking

    logger.info(f"[{request_id}] Transcription request from {client_ip}: {file.filename}")

    tmp_path: Optional[str] = None

    try:
        # Read and validate file
        contents = await file.read()
        validate_audio_file(file, contents)

        # Create temporary file
        if not file.filename:
            raise ValidationError("No filename provided", "MISSING_FILENAME")
        file_extension = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        logger.debug(f"[{request_id}] Saved to temporary file: {tmp_path}")

        # Transcribe audio
        transcript = await transcribe_audio_file(tmp_path, client_ip)

        response = {
            "transcript": transcript,
            "metadata": {
                "filename": file.filename,
                "file_size_bytes": len(contents),
                "model_used": WHISPER_MODEL_NAME,
                "request_id": request_id
            }
        }

        logger.info(f"[{request_id}] Transcription successful for {client_ip}")
        return response

    except (ValidationError, TranscriptionError):
        # Re-raise custom exceptions to be handled by exception handlers
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error for {client_ip}: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.debug(f"[{request_id}] Cleaned up temporary file: {tmp_path}")
            except Exception as e:
                logger.warning(f"[{request_id}] Failed to clean up {tmp_path}: {e}")


@app.get("/debug/client-info", tags=["Debug"])
async def get_client_info(request: Request) -> Dict[str, Any]:
    """
    Debug endpoint to check client information and request headers.

    Args:
        request: FastAPI request object

    Returns:
        Client information including IP and headers
    """
    try:
        client_ip = get_client_ip(request)

        info = {
            "client_ip": client_ip,
            "headers": dict(request.headers),
            "method": request.method,
            "url": str(request.url),
            "user_agent": request.headers.get("user-agent", "unknown")
        }

        logger.debug(f"Debug info requested from {client_ip}")
        return info

    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return {"error": "Failed to get client info", "message": str(e)}


if __name__ == "__main__":
    # For local development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
