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
    if len(sys.argv) < 2:
        print("Usage: python minimal-client.py <server_url> [audio_file]")
        print("Example: python minimal-client.py http://localhost:8000 harvard.wav")
        sys.exit(1)

    # Remote server configuration from command line
    remote_server = sys.argv[1]

    # Default audio file (can be overridden by command line argument)
    audio_file = "harvard.wav"
    
    # Allow command line argument for different audio file
    if len(sys.argv) > 2:
        audio_file = sys.argv[2]

    # First check if the server is healthy
    print(f"Checking server health at {remote_server}...")
    if not check_health(remote_server):
        print("Server is not healthy. Exiting.")
        sys.exit(1)
    print("Server is healthy!")

    # Attempt transcription
    print(f"Transcribing {audio_file}...")
    transcript = transcribe_audio(audio_file, remote_server)

    if transcript:
        print("\nTranscription result:")
        print(transcript)
    else:
        print("Transcription failed")

if __name__ == "__main__":
    main()
