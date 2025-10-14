# ZoomInfo SE3 Take-Home: Build and Ship an Open-Source Speech-to-Text Service

## Introduction

At ZoomInfo we value real-world experience and how candidates handle real challenges. This exercise is designed to evaluate your ability to design, code, test, deploy, and consume a working application.

## Time Expectations

- This task is not time-limited, but we believe it can be completed in ~3 to 5 hours.
- Use any assistant tools you like (including AI). We encourage AI-assisted “vibe coding” in our environment.

## What to Deliver

1.  **Git repository we can review:**
    -   Source code
    -   Tests
    -   CI/CD configuration
    -   README with setup, run, deploy, and usage instructions

2.  **Publicly accessible service:**
    -   You may host in your own environment (we need full access to the deployed artifacts for review), OR
    -   Use our provided Ubuntu Server on AWS:
        -   It’s internet-accessible; SSH is open and all ports are open externally.
        -   If you choose this option, send us your public SSH key. We will return the server’s public IP.

3.  **Documentation:**
    -   How to run locally
    -   How to deploy
    -   How to call the service (examples)
    -   Any prerequisites

4.  **Software engineering standards:**
    -   Code quality and formatting
    -   Meaningful tests
    -   Clear error handling and logging

5.  **CI/CD:**
    -   An automated process that builds, tests, and deploys to the chosen server

## Business Requirement

As a Sales Representative, I want to record a call on my computer and get a transcript of what was said.

## Functional Requirements (Must-Haves)

1.  **Build a service that transcribes audio input and returns text:**
    -   Use an open-source speech-to-text solution (for example: Whisper/whisper.cpp/faster-whisper, Vosk, or another open-source option of your choice).
    -   Do not use paid or hosted external transcription services.
    -   Expose a simple HTTP API to accept an audio stream or file and return the transcript.
    -   Response format is your choice (JSON or Markdown). Document the format.
    -   Provide a health endpoint for basic readiness (e.g., GET /health).

2.  **Minimal usage example:**
    -   Include a script or command that calls your service with a preset/local audio file and prints/returns the transcript.

3.  **Bonus (optional, if time allows):**
    -   Build a simple client application that records speech on the user’s computer (desktop or browser) and sends it to your service, then displays the transcript.

## Non-Functional Requirements and Constraints

-   The service must be publicly accessible for our validation.
-   Keep secrets out of source control; use environment variables or a secrets manager.
-   Include basic logging and error handling (e.g., invalid audio, unsupported format).
-   Document supported audio formats and any size/runtime limits.
-   Make it easy to test with `curl` or an equivalent tool.

## CI/CD Expectations

-   Provide a pipeline (e.g., GitHub Actions) that:
    -   Builds and tests the code on push
    -   Packages artifacts (container image or binary)
    -   Deploys to the target server (our Ubuntu server or your environment)
-   If deploying to our Ubuntu server, include clear deploy steps (e.g., `docker-compose` or `systemd` service). If using Docker, include `Dockerfile` and compose file.

## Access and Deployment (If Using Our AWS Ubuntu Server)

-   Send us your public SSH key.
-   We will send you the server’s public IP.
-   Deploy your service and provide the public URL and port.
-   Tell us how to verify it end-to-end.

## What to Include in Your README

-   Architecture overview (one paragraph is enough)
-   Local development steps
-   How to run tests
-   How to start the service locally
-   Deployment steps (exact commands)
-   Example usage:
    -   Health check (e.g., `curl GET /health`)
    -   Transcription with a preset audio file (e.g., `curl` or a script)
-   Notes on trade-offs and what you would do next with more time

## Acceptance Criteria (We Will Verify)

-   We can clone the repo and understand how to run and deploy from the README.
-   Health endpoint returns `OK`.
-   Posting or streaming an audio file to your API returns a transcript (JSON or Markdown, as documented).
-   Minimal example works: calling the service with a preset audio file returns a transcript.
-   CI/CD runs on push and can deploy to the chosen server.
-   Bonus: the optional client records from the local mic and successfully gets a transcript from your service.
