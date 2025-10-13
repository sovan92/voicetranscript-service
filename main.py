from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
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


app = FastAPI()

logger.info("Loading transcription model...")
# Load the model once when the application starts
# This is more efficient than loading it for each request.
model_name = os.getenv("WHISPER_MODEL", "tiny")
model = WhisperModel(model_name, device="cpu", compute_type="int8")
logger.info(f"Transcription model '{model_name}' loaded successfully.")


SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "ogg", "flac"]

@app.get("/health")
def health():
    logger.info("Health check endpoint was called.")
    return {"status": "ok"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    logger.info(f"Received transcription request for file: {file.filename}")
    ext = file.filename.split(".")[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported audio format '{ext}' for file: {file.filename}")
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")

    tmp_path = None
    try:
        # Create a temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(await file.read())
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
