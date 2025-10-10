from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import whisper
import tempfile
import os
import logging

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

model = whisper.load_model("base")
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
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        result = model.transcribe(tmp_path)
        os.remove(tmp_path)
        return JSONResponse({"transcript": result["text"]})
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")

