import requests
import sys
import os

def check_health(base_url):
    """Check if the server is healthy"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        return response.json().get("status") == "ok"
    except requests.RequestException as e:
        print(f"Error checking server health: {e}")
        return False

def transcribe_audio(file_path, base_url):
    """Transcribe an audio file using the remote service"""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return None

    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "audio/wav")}
            response = requests.post(f"{base_url}/transcribe", files=files, timeout=30)
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.json().get("transcript")
    except requests.RequestException as e:
        print(f"Error during transcription: {e}")
        return None

def main():
    # Remote server configuration
    REMOTE_SERVER = "http://54.245.18.107:8000"
    
    # Default audio file (can be overridden by command line argument)
    audio_file = "harvard.wav"
    
    # Allow command line argument for different audio file
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]

    # First check if the server is healthy
    print("Checking server health...")
    if not check_health(REMOTE_SERVER):
        print("Server is not healthy. Exiting.")
        sys.exit(1)
    print("Server is healthy!")

    # Attempt transcription
    print(f"Transcribing {audio_file}...")
    transcript = transcribe_audio(audio_file, REMOTE_SERVER)
    
    if transcript:
        print("\nTranscription result:")
        print(transcript)
    else:
        print("Transcription failed")

if __name__ == "__main__":
    main()
