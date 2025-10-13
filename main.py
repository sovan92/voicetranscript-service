from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
import tempfile
import os
import logging

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# Load the model once when the application starts
# This is more efficient than loading it for each request.
model = WhisperModel("base", device="cpu", compute_type="int8")

SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "ogg", "flac"]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported format: {ext}")
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")

    tmp_path = None
    try:
        # Create a temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Transcribe the audio file
        segments, info = model.transcribe(tmp_path, beam_size=5)

        # Join the transcribed segments into a single string
        transcript = "".join(segment.text for segment in segments)

        return JSONResponse({"transcript": transcript})
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")
    finally:
        # Clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
