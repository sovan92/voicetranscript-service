import requests
import sys

AUDIO_FILE = "sample.wav"  # Change to your preset audio file
API_URL = "http://127.0.0.1:8000/transcribe"

with open(AUDIO_FILE, "rb") as f:
    files = {"file": (AUDIO_FILE, f, "audio/wav")}
    response = requests.post(API_URL, files=files)
    print("Transcript:", response.json().get("transcript"))

