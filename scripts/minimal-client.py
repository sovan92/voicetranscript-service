#!/usr/bin/env python3
"""
Enhanced minimal client for the Voice Transcription Service.

This client provides a command-line interface for transcribing audio files
using the voice transcription service with proper error handling and logging.
"""

import argparse
import sys
import requests
import json
from pathlib import Path
from typing import Optional, Dict, Any
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TranscriptionClient:
    """Client for interacting with the voice transcription service."""

    def __init__(self, base_url: str, timeout: int = 60):
        """
        Initialize the transcription client.

        Args:
            base_url: Base URL of the transcription service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'VoiceTranscription-Client/1.0'
        })

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health status of the transcription service.

        Returns:
            Dict containing health information

        Raises:
            requests.RequestException: If health check fails
        """
        try:
            logger.info("Checking service health...")
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()

            health_data = response.json()
            logger.info(f"Service status: {health_data.get('status', 'unknown')}")

            return health_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {e}")
            raise

    def transcribe_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Transcribe an audio file.

        Args:
            file_path: Path to the audio file to transcribe

        Returns:
            Dict containing transcription results

        Raises:
            FileNotFoundError: If the audio file doesn't exist
            requests.RequestException: If transcription request fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Check file size
        file_size = file_path.stat().st_size
        max_size = 10 * 1024 * 1024  # 10MB

        if file_size > max_size:
            raise ValueError(f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds 10MB limit")

        logger.info(f"Transcribing file: {file_path} ({file_size} bytes)")

        try:
            with open(file_path, 'rb') as audio_file:
                files = {
                    'file': (file_path.name, audio_file, self._get_content_type(file_path))
                }

                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/transcribe",
                    files=files,
                    timeout=self.timeout
                )
                duration = time.time() - start_time

                response.raise_for_status()

                result = response.json()
                logger.info(f"Transcription completed in {duration:.2f} seconds")

                return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Transcription failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Error details: {error_data}")
                except (json.JSONDecodeError, AttributeError):
                    logger.error(f"Response text: {e.response.text}")
            raise

    def _get_content_type(self, file_path: Path) -> str:
        """
        Get appropriate content type for audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            str: MIME content type
        """
        extension = file_path.suffix.lower()
        content_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mp3',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.webm': 'audio/webm',
            '.mp4': 'video/mp4'
        }
        return content_types.get(extension, 'application/octet-stream')


def print_results(result: Dict[str, Any], verbose: bool = False) -> None:
    """
    Print transcription results in a formatted way.

    Args:
        result: Transcription result dictionary
        verbose: Whether to print verbose information
    """
    print("\n" + "="*50)
    print("TRANSCRIPTION RESULT")
    print("="*50)

    transcript = result.get('transcript', '')
    print(f"\nTranscript:\n{transcript}")

    if verbose and 'metadata' in result:
        metadata = result['metadata']
        print(f"\nMetadata:")
        print(f"  Filename: {metadata.get('filename', 'N/A')}")
        print(f"  File size: {metadata.get('file_size_bytes', 'N/A')} bytes")
        print(f"  Model used: {metadata.get('model_used', 'N/A')}")
        print(f"  Request ID: {metadata.get('request_id', 'N/A')}")

    print("="*50)


def main():
    """Main function for the transcription client."""
    parser = argparse.ArgumentParser(
        description="Voice Transcription Service Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s http://localhost:8000 audio.wav
  %(prog)s https://api.example.com audio.mp3 --verbose
  %(prog)s http://localhost:8000 recording.m4a --health-check --timeout 120
        """
    )

    parser.add_argument(
        'base_url',
        help='Base URL of the transcription service'
    )

    parser.add_argument(
        'audio_file',
        nargs='?',
        help='Path to the audio file to transcribe'
    )

    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Perform health check before transcription'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='Request timeout in seconds (default: 60)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Save transcript to file'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.audio_file and not args.health_check:
        parser.error("Audio file is required unless --health-check is specified")

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize client
        client = TranscriptionClient(args.base_url, args.timeout)

        # Perform health check if requested
        if args.health_check:
            health_data = client.check_health()

            if args.verbose:
                print("\nHealth Check Results:")
                print(json.dumps(health_data, indent=2))

            if health_data.get('status') != 'healthy':
                logger.warning("Service is not healthy!")
                if not args.audio_file:
                    sys.exit(1)

        # Transcribe audio file if provided
        if args.audio_file:
            audio_path = Path(args.audio_file)

            # Transcribe the file
            result = client.transcribe_file(audio_path)

            # Print results
            print_results(result, args.verbose)

            # Save to file if requested
            if args.output:
                transcript = result.get('transcript', '')
                args.output.write_text(transcript, encoding='utf-8')
                logger.info(f"Transcript saved to: {args.output}")

        logger.info("Client completed successfully")

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        logger.error(f"Failed to connect to service at {args.base_url}")
        logger.error("Please check that the service is running and the URL is correct")
        sys.exit(1)
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out after {args.timeout} seconds")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
