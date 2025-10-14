#!/usr/bin/env python3
"""
Test script to verify rate limiting functionality
"""
import requests
import time
import sys
import os

def test_rate_limit(base_url="http://localhost:8000", num_requests=10):
    """Test the rate limiter by making multiple requests"""

    # Use a test file (you can create a small wav file or use an existing one)
    test_file = "harvard.wav"

    if not os.path.exists(test_file):
        print(f"Test file {test_file} not found. Please ensure it exists.")
        return

    print(f"Testing rate limiter with {num_requests} requests...")
    print(f"Rate limit is set to 5/minute")
    print("-" * 50)

    success_count = 0
    rate_limited_count = 0

    for i in range(num_requests):
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (test_file, f, 'audio/wav')}
                response = requests.post(f"{base_url}/transcribe", files=files, timeout=30)

            if response.status_code == 200:
                success_count += 1
                print(f"Request {i+1}: SUCCESS (200)")
            elif response.status_code == 429:
                rate_limited_count += 1
                print(f"Request {i+1}: RATE LIMITED (429)")
                print(f"  Response: {response.text}")
            else:
                print(f"Request {i+1}: ERROR ({response.status_code}) - {response.text}")

        except Exception as e:
            print(f"Request {i+1}: EXCEPTION - {e}")

        # Small delay between requests
        time.sleep(0.5)

    print("-" * 50)
    print(f"Results:")
    print(f"  Successful requests: {success_count}")
    print(f"  Rate limited requests: {rate_limited_count}")
    print(f"  Total requests: {num_requests}")

    if rate_limited_count == 0 and num_requests > 5:
        print("WARNING: No rate limiting detected! There may be an issue with the rate limiter.")
    elif rate_limited_count > 0:
        print("Rate limiting is working correctly!")

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    num_requests = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    test_rate_limit(base_url, num_requests)
