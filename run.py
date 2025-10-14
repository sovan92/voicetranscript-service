#!/usr/bin/env python3
"""
Entry point for the Voice Transcription Service.

This script provides a convenient way to start the application
with proper configuration and error handling.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point for the application."""
    try:
        import uvicorn
        from voicetranscript.main import app

        # Run the application
        uvicorn.run(
            "voicetranscript.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            app_dir=str(src_path)
        )
    except ImportError as e:
        print(f"Error importing dependencies: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
